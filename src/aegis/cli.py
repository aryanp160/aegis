import datetime
import json
import logging
import platform
import sys
from pathlib import Path
from typing import Annotated

import sqlglot
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from aegis import __version__
from aegis.config import load_config
from aegis.engine import RuleEngine
from aegis.logging import setup_logging
from aegis.parser import SqlParser, discover_migration_files
from aegis.rules.registry import RuleRegistry

app = typer.Typer(
    name="aegis",
    help="Aegis: A production-quality static analyzer for Python SQL migrations.",
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
    version_info = (
        f"[bold blue]Aegis[/bold blue] version: [green]{__version__}[/green]\n"
        f"  [bold]Python:[/bold]      {platform.python_version()} ({python_impl})\n"
        f"  [bold]Platform:[/bold]    {platform.platform()}\n"
        f"  [bold]SQLGlot:[/bold]     {sqlglot.__version__}"
    )
    console.print(version_info)


def version_callback(value: bool) -> None:
    """Callback to print the package version and exit."""
    if value:
        _print_version()
        raise typer.Exit()


@app.callback()
def main(
    version_opt: bool | None = typer.Option(  # noqa: ARG001
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show Aegis version and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose debug logging.",
    ),
) -> None:
    """
    🛡️ **Aegis** - Production-quality static analyzer for Python SQL migrations.

    Aegis parses your migration files, builds abstract syntax trees (ASTs), and
    inspects schema changes against safety rules to prevent destructive database
    schema modifications (e.g., dropping columns, locking tables, unsafe type changes).
    """
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    if verbose:
        logger.debug("Verbose logging enabled")


@app.command()
def version() -> None:
    """Show the version of Aegis and execution environment metadata."""
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


@app.command(name="lint")
def lint(
    targets: Annotated[
        list[Path],
        typer.Argument(
            help="One or more SQL migration files or directories to lint.",
            show_default=False,
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (text, json)."),
    ] = "text",
    severity: Annotated[
        str | None,
        typer.Option(
            "--severity",
            "-s",
            help="Filter violations by minimum severity (error, warning, info).",
        ),
    ] = None,
    ignore: Annotated[
        list[str] | None,
        typer.Option(
            "--ignore",
            "-i",
            help="List of rule codes to ignore/suppress (comma-separated).",
        ),
    ] = None,
    exclude: Annotated[
        list[Path] | None,
        typer.Option("--exclude", "-e", help="List of paths to exclude from linting."),
    ] = None,
) -> None:
    """
    Lint SQL migration files for rule violations and print diagnostics.

    Inspects SQL scripts recursively, detecting destructive or non-backwards-compatible
    database operations.

    ### Examples
    ```bash
    # Lint a specific file
    aegis lint migrations/0001_init.sql

    # Lint a whole directory
    aegis lint migrations/

    # Exclude test directories and get JSON output
    aegis lint migrations/ --exclude migrations/test/ --format json
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

    ignored_set = set()
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


@app.command(name="explain")
def explain(
    rule_id: Annotated[
        str,
        typer.Argument(help="The code of the rule to explain (e.g., AEG-101)."),
    ],
) -> None:
    """
    Show detailed documentation, risk assessment, and remediation steps for a rule.

    ### Examples
    ```bash
    aegis explain AEG-101
    aegis explain AEG-105
    ```
    """
    config = load_config()

    rule_cls = RuleRegistry.get_rule(rule_id.strip().upper())
    if not rule_cls:
        # Search case-insensitively
        norm_search = rule_id.lower().strip()
        for code, r_cls in RuleRegistry._rules.items():
            if (
                code.lower() == norm_search
                or r_cls.metadata.name.lower() == norm_search
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
        if meta.code in overrides and overrides[meta.code].severity is not None:
            severity = overrides[meta.code].severity.value

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
