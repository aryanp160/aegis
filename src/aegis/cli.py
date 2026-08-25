import datetime
import json
import logging
import platform
import sys
from pathlib import Path
from typing import Annotated

import sqlglot
import typer
from rich.box import ROUNDED
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

import aegis.rules  # noqa: F401 - triggers rule registration
from aegis import __version__
from aegis.config import load_config
from aegis.engine import RuleEngine
from aegis.logging import setup_logging
from aegis.parser import SqlParser, discover_migration_files
from aegis.rules.enums import Category
from aegis.rules.registry import RuleRegistry

app = typer.Typer(
    name="aegis",
    help="🛡️ Aegis: Production-quality static analyzer for Python SQL migrations.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
console = Console()
logger = logging.getLogger("aegis")


def get_err_console() -> Console:
    """Dynamically get Console writing to the current sys.stderr stream."""
    return Console(file=sys.stderr)


def _print_version() -> None:
    """Prints Aegis version and platform/dependency metadata."""
    python_impl = platform.python_implementation()
    sqlglot_ver = getattr(sqlglot, "__version__", "unknown")
    version_content = (
        f"[bold blue]Aegis Version:[/bold blue]  "
        f"[bold green]{__version__}[/bold green]\n"
        f"[bold blue]Python Runtime:[/bold blue] "
        f"{platform.python_version()} ({python_impl})\n"
        f"[bold blue]Platform OS:[/bold blue]    {platform.platform()}\n"
        f"[bold blue]SQLGlot Parser:[/bold blue] {sqlglot_ver}"
    )
    panel = Panel(
        version_content,
        title="[bold blue]🛡️  Aegis Migration Analyzer[/bold blue]",
        title_align="left",
        border_style="blue",
        expand=False,
    )
    console.print(panel)


def version_callback(value: bool) -> None:
    """Callback to print the package version and exit."""
    if value:
        _print_version()
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version_opt: bool | None = typer.Option(  # noqa: ARG001
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show Aegis version and system metadata, then exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose debug logging output.",
    ),
) -> None:
    """
    🛡️ **Aegis** - Production-quality static analyzer for Python SQL migrations.

    Aegis inspects your database migration files, builds Abstract Syntax Trees (ASTs),
    and evaluates schema changes against safety rules to prevent destructive database
    modifications (e.g., dropping columns, locking tables, unsafe column type changes).

    ### Quick Usage Examples
    ```bash
    # Lint a directory containing SQL migrations
    aegis lint migrations/

    # List all active static analysis rules
    aegis rules

    # View remediation documentation for a specific rule
    aegis explain AEG-101
    ```
    """
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    if verbose:
        logger.debug("Verbose logging enabled")


@app.command(name="version", rich_help_panel="Utility Commands")
def version() -> None:
    """
    Show Aegis version and execution environment metadata.

    ### Examples
    ```bash
    aegis version
    ```
    """
    _print_version()


def _is_excluded(path: Path, excludes: list[Path] | None) -> bool:
    if not excludes:
        return False
    try:
        resolved_path = path.resolve()
    except Exception:
        resolved_path = path.absolute()
    for excl in excludes:
        try:
            resolved_excl = excl.resolve()
        except Exception:
            resolved_excl = excl.absolute()
        if resolved_excl == resolved_path:
            return True
        if resolved_excl.is_dir() and resolved_excl in resolved_path.parents:
            return True
    return False


@app.command(name="lint", rich_help_panel="Analysis Commands")
def lint(
    targets: Annotated[
        list[Path] | None,
        typer.Argument(
            help="One or more SQL migration files or directories to analyze.",
            show_default=False,
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help=(
                "Output format scheme ('text' for styled terminal output, "
                "'json' for machine reports)."
            ),
        ),
    ] = "text",
    severity: Annotated[
        str | None,
        typer.Option(
            "--severity",
            "-s",
            help="Filter violations by minimum severity ('error', 'warning', 'info').",
        ),
    ] = None,
    ignore: Annotated[
        list[str] | None,
        typer.Option(
            "--ignore",
            "-i",
            help=(
                "List of rule codes to ignore/suppress "
                "(comma-separated, e.g., AEG-101,AEG-107)."
            ),
        ),
    ] = None,
    exclude: Annotated[
        list[Path] | None,
        typer.Option(
            "--exclude",
            "-e",
            help="Paths to exclude from linting. Can be specified multiple times.",
        ),
    ] = None,
) -> None:
    """
    Lint SQL migration files for rule violations and print safety diagnostics.

    Scans SQL migration scripts recursively, parsing ASTs and detecting destructive
    or non-backwards-compatible database operations before deployment.

    ### Examples
    ```bash
    # Lint a specific migration script
    aegis lint migrations/0001_init.sql

    # Recursively lint a directory of migration files
    aegis lint migrations/

    # Generate structured JSON report for CI/CD pipelines
    aegis lint migrations/ --format json

    # Filter violations by severity and exclude test directories
    aegis lint migrations/ --severity error --exclude migrations/test/
    ```
    """
    if not targets:
        get_err_console().print(
            "[bold red]Error:[/bold red] No targets specified. "
            "Please provide at least one file or directory to lint."
        )
        raise typer.Exit(code=2)

    if format not in ("text", "json"):
        get_err_console().print(
            "[bold red]Error:[/bold red] Invalid format option: "
            f"[yellow]'{format}'[/yellow]. "
            "Supported formats: 'text', 'json'."
        )
        raise typer.Exit(code=2)

    severity_filter = severity.lower() if severity else None
    if severity_filter and severity_filter not in ("error", "warning", "info"):
        get_err_console().print(
            "[bold red]Error:[/bold red] Invalid severity level: "
            f"[yellow]'{severity}'[/yellow]. "
            "Supported severity levels: 'error', 'warning', 'info'."
        )
        raise typer.Exit(code=2)

    ignored_set: set[str] = set()
    if ignore:
        for item in ignore:
            for part in item.split(","):
                ignored_set.add(part.strip().upper())

    files_to_lint: list[Path] = []
    for target in targets:
        if _is_excluded(target, exclude):
            continue

        if not target.exists():
            get_err_console().print(
                "[bold red]Error:[/bold red] Target path does not exist: "
                f"[yellow]'{escape(str(target))}'[/yellow]"
            )
            raise typer.Exit(code=2)

        if target.is_file():
            files_to_lint.append(target)
        elif target.is_dir():
            try:
                discovered = discover_migration_files(target)
                for f in discovered:
                    if not _is_excluded(f, exclude):
                        files_to_lint.append(f)
            except Exception as e:
                get_err_console().print(
                    "[bold red]Error:[/bold red] Failed to discover files in "
                    f"[yellow]'{escape(str(target))}'[/yellow]: {e}"
                )
                raise typer.Exit(code=2) from e
        else:
            get_err_console().print(
                "[bold red]Error:[/bold red] Target path is not a file or "
                f"directory: [yellow]'{escape(str(target))}'[/yellow]"
            )
            raise typer.Exit(code=2)

    parser = SqlParser()
    config = load_config()
    migrations = []
    diagnostics_output = []

    for file_path in files_to_lint:
        try:
            result = parser.parse(file_path)
            if not result.success:
                for err in result.errors:
                    diagnostics_output.append(
                        {"file": str(file_path), "message": err, "severity": "error"}
                    )
            else:
                if result.migration:
                    migrations.append(result.migration)
        except Exception as e:
            get_err_console().print(
                "[bold red]Internal error[/bold red] processing "
                f"[yellow]'{escape(str(file_path))}'[/yellow]: {e}"
            )
            raise typer.Exit(code=2) from e

    engine = RuleEngine()
    analysis_result = engine.analyze(migrations, config)

    # Filter violations based on CLI arguments
    severity_weights = {
        "error": 3,
        "warning": 2,
        "info": 1,
    }
    min_weight = severity_weights.get(severity_filter or "", 0)

    filtered_violations = []
    for v in analysis_result.violations:
        if v.code in ignored_set:
            continue
        v_severity = v.severity.value.lower()
        if severity_weights.get(v_severity, 0) < min_weight:
            continue
        filtered_violations.append(v)

    has_failures = bool(filtered_violations or diagnostics_output)

    if format == "json":
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        violations_json = []
        for v in filtered_violations:
            violations_json.append({
                "file": str(v.path),
                "line": v.line,
                "column": v.column,
                "rule": v.code,
                "severity": v.severity.value,
                "message": v.message,
            })
        output_schema = {
            "metadata": {"version": __version__, "timestamp": timestamp},
            "summary": {
                "files_scanned": len(files_to_lint),
                "violations_count": len(filtered_violations),
                "success": not has_failures,
            },
            "violations": violations_json,
            "diagnostics": diagnostics_output,
        }
        print(json.dumps(output_schema, indent=2))
    else:
        for diag in diagnostics_output:
            console.print(
                "[bold red]ERROR[/bold red] - "
                f"[yellow]{escape(diag['file'])}[/yellow]: "
                f"\\[syntax_error] {escape(diag['message'])}"
            )
        for viol in filtered_violations:
            console.print(viol.render())
            console.print()

    if has_failures:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command(name="explain", rich_help_panel="Analysis Commands")
def explain(
    rule_id: Annotated[
        str,
        typer.Argument(
            help=(
                "Rule code (e.g., AEG-101) or rule name "
                "(e.g., allow_drop_table) to explain."
            ),
        ),
    ],
) -> None:
    """
    Display detailed documentation, risk assessment, and remediation for a rule.

    Fetches full documentation for a given Aegis rule identifier or rule name,
    including rule severity, category, risk explanation, remediation steps,
    and safe/unsafe SQL examples.

    ### Examples
    ```bash
    # Explain a rule by code identifier
    aegis explain AEG-101

    # Explain a rule by rule name
    aegis explain allow_drop_table
    ```
    """
    config = load_config()

    norm_search = rule_id.strip().upper()
    rule_cls = RuleRegistry.get_rule(norm_search)

    if not rule_cls:
        # Search case-insensitively across rules catalog
        clean_input = rule_id.lower().strip().replace("-", "_").replace(" ", "_")
        stripped_input = clean_input.replace("allow_", "").replace("_", "")

        for code, r_cls in RuleRegistry._rules.items():
            meta = r_cls.metadata
            name_clean = meta.name.lower().replace("-", "_").replace(" ", "_")
            code_clean = code.lower().replace("-", "_")
            cls_clean = r_cls.__name__.lower()
            cls_compact = cls_clean.replace("_", "")

            if (
                clean_input == code_clean
                or clean_input == name_clean
                or clean_input in name_clean
                or clean_input in cls_clean
                or (stripped_input and stripped_input in cls_compact)
            ):
                rule_cls = r_cls
                break

    if not rule_cls:
        get_err_console().print(
            "[bold red]Error:[/bold red] Unknown rule "
            f"[yellow]'{escape(rule_id)}'[/yellow]"
        )
        raise typer.Exit(code=2)

    meta = rule_cls.metadata

    # Check config overrides for severity
    severity = meta.severity.value
    if config and hasattr(config, "rules"):
        overrides = config.rules.get_overrides()
        if meta.code in overrides:
            override = overrides[meta.code]
            if override.severity is not None:
                severity = override.severity.value

    sev_color = "red" if severity.lower() == "error" else "yellow"

    panel_content = (
        f"[bold blue]Code:[/bold blue]        {meta.code}\n"
        f"[bold blue]Rule Name:[/bold blue]   {meta.name}\n"
        f"[bold blue]Category:[/bold blue]    {meta.category.value.title()}\n"
        f"[bold blue]Severity:[/bold blue]    "
        f"[{sev_color}]{severity.upper()}[/{sev_color}]\n\n"
        f"[bold]Description:[/bold]\n{meta.description}\n\n"
        f"[bold]Why It Matters / Risk:[/bold]\n{meta.risk}\n\n"
        f"[bold]Explanation:[/bold]\n{meta.explanation}\n\n"
        f"[bold]Remediation:[/bold]\n{meta.remediation}\n\n"
        f"[bold]Unsafe Example:[/bold]\n[red]{meta.unsafe_sql}[/red]\n\n"
        f"[bold]Safe Example:[/bold]\n[green]{meta.safe_sql}[/green]\n\n"
        f"[bold blue]Documentation:[/bold blue] {meta.documentation_url}"
    )

    console.print(
        Panel(
            panel_content,
            title=f"[bold]Rule Documentation: {meta.code}[/bold]",
            title_align="left",
            border_style="blue",
            expand=False,
        )
    )


@app.command(name="rules", rich_help_panel="Analysis Commands")
def list_rules(
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help=(
                "Filter rules by category ('destructive', 'performance', "
                "'security', 'compatibility', 'style', 'high_risk', 'operational')."
            ),
        ),
    ] = None,
    severity: Annotated[
        str | None,
        typer.Option(
            "--severity",
            "-s",
            help="Filter rules by default severity ('error', 'warning', 'info').",
        ),
    ] = None,
) -> None:
    """
    List registered static analysis rules and summary statistics.

    Displays a formatted catalog of all active static analysis rules in Aegis,
    allowing filtering by rule category or severity level.

    ### Examples
    ```bash
    # List all registered rules
    aegis rules

    # Filter rules by category
    aegis rules --category destructive

    # Filter rules by severity level
    aegis rules --severity error
    ```
    """
    all_rules = list(RuleRegistry._rules.values())

    cat_filter = category.lower().strip() if category else None
    sev_filter = severity.lower().strip() if severity else None

    enum_categories = {c.value.lower() for c in Category}
    alias_map = {
        "high_risk": ["destructive", "high_risk"],
        "operational": ["performance", "operational"],
        "best_practices": ["style", "best_practices"],
    }
    valid_categories = enum_categories.union(alias_map.keys())

    if cat_filter and cat_filter not in valid_categories:
        get_err_console().print(
            "[bold red]Error:[/bold red] Invalid category filter: "
            f"[yellow]'{escape(category or '')}'[/yellow]. "
            f"Supported categories: {', '.join(sorted(valid_categories))}."
        )
        raise typer.Exit(code=2)

    if sev_filter and sev_filter not in ("error", "warning", "info"):
        get_err_console().print(
            "[bold red]Error:[/bold red] Invalid severity filter: "
            f"[yellow]'{escape(severity or '')}'[/yellow]. "
            "Supported severity levels: 'error', 'warning', 'info'."
        )
        raise typer.Exit(code=2)

    allowed_cats = alias_map.get(cat_filter, [cat_filter]) if cat_filter else []

    table = Table(
        box=ROUNDED,
        title="[bold blue]🛡️ Aegis Static Analysis Rules Catalog[/bold blue]",
        header_style="bold cyan",
    )

    table.add_column("Code", style="bold blue", justify="left")
    table.add_column("Rule Name", style="bold white", justify="left")
    table.add_column("Category", style="magenta", justify="left")
    table.add_column("Severity", justify="left")
    table.add_column("Description Summary", justify="left")

    matching_count = 0
    for rule_cls in sorted(all_rules, key=lambda r: r.metadata.code):
        meta = rule_cls.metadata

        rule_cat = meta.category.value.lower()
        rule_sev = meta.severity.value.lower()

        if (
            allowed_cats
            and rule_cat not in allowed_cats
            and cat_filter not in allowed_cats
        ):
            continue
        if sev_filter and rule_sev != sev_filter:
            continue

        matching_count += 1

        sev_style = "bold red" if rule_sev == "error" else "bold yellow"
        if rule_sev == "info":
            sev_style = "bold blue"

        # Short summary of description
        desc = meta.description.split("\n")[0]
        if len(desc) > 60:
            desc = desc[:57] + "..."

        table.add_row(
            meta.code,
            meta.name,
            meta.category.value.title(),
            f"[{sev_style}]{meta.severity.value.upper()}[/{sev_style}]",
            desc,
        )

    console.print(table)
    summary_text = (
        f"[dim]Displayed {matching_count} of {len(all_rules)} "
        "registered static analysis rules.[/dim]"
    )
    console.print(summary_text)
