import datetime
import json
import logging
from pathlib import Path
from typing import Annotated

import sys
import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from aegis import __version__
from aegis.config import load_config
from aegis.logging import setup_logging
from aegis.parser import SqlParser, discover_migration_files
from aegis.rules import check_rules

app = typer.Typer(
    name="aegis",
    help="Aegis: A production-quality static analyzer for Python SQL migrations.",
    no_args_is_help=True,
)
console = Console()
logger = logging.getLogger("aegis")


def get_err_console() -> Console:
    """Dynamically get Console writing to the current sys.stderr stream."""
    return Console(file=sys.stderr)


def version_callback(value: bool) -> None:
    """Callback to print the package version and exit."""
    if value:
        console.print(
            f"[bold blue]Aegis[/bold blue] version: [green]{__version__}[/green]"
        )
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
    """Aegis static analyzer for SQL migration safety."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    if verbose:
        logger.debug("Verbose logging enabled")


@app.command()
def version() -> None:
    """Show the version of Aegis."""
    console.print(f"[bold blue]Aegis[/bold blue] version: [green]{__version__}[/green]")


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
            help="Filter violations by minimum severity (error, warning).",
        ),
    ] = None,
    ignore: Annotated[
        list[str] | None,
        typer.Option(
            "--ignore",
            "-i",
            help="List of rule IDs to ignore/suppress (comma-separated).",
        ),
    ] = None,
    exclude: Annotated[
        list[Path] | None,
        typer.Option("--exclude", "-e", help="List of paths to exclude from linting."),
    ] = None,
) -> None:
    """Lint SQL migration files for rule violations and print diagnostics.

    Examples:
        aegis lint migration.sql
        aegis lint migrations/ -f json
        aegis lint migrations/ -s error -i allow_drop_table
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
    if severity_filter and severity_filter not in ("error", "warning"):
        get_err_console().print(
            "[bold red]Error:[/bold red] Invalid severity level: "
            f"[yellow]'{severity}'[/yellow]. "
            "Supported severity levels: 'error', 'warning'."
        )
        raise typer.Exit(code=2)

    ignored_set = set()
    if ignore:
        for item in ignore:
            for part in item.split(","):
                ignored_set.add(part.strip().lower().replace("-", "_"))

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
    violations_output = []
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
                migration = result.migration
                if migration:
                    violations = check_rules(migration, config)
                    for v in violations:
                        norm_rule = v.rule_name.lower().replace("-", "_")
                        if norm_rule in ignored_set:
                            continue

                        v_severity = v.severity.lower()
                        if severity_filter == "error" and v_severity != "error":
                            continue

                        violations_output.append(
                            {
                                "file": str(v.file_path),
                                "rule": v.rule_name,
                                "severity": v.severity,
                                "message": v.message,
                            }
                        )
        except Exception as e:
            get_err_console().print(
                "[bold red]Internal error[/bold red] processing "
                f"[yellow]'{escape(str(file_path))}'[/yellow]: {e}"
            )
            raise typer.Exit(code=2) from e

    has_failures = bool(violations_output or diagnostics_output)

    if format == "json":
        timestamp = datetime.datetime.now(datetime.UTC).isoformat()
        output_schema = {
            "metadata": {"version": __version__, "timestamp": timestamp},
            "summary": {
                "files_scanned": len(files_to_lint),
                "violations_count": len(violations_output),
                "success": not has_failures,
            },
            "violations": violations_output,
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
        for viol in violations_output:
            sev_color = "red" if viol["severity"].lower() == "error" else "yellow"
            console.print(
                f"[bold {sev_color}]{viol['severity'].upper()}[/bold {sev_color}] - "
                f"[yellow]{escape(viol['file'])}[/yellow]: "
                f"\\[{escape(viol['rule'])}] {escape(viol['message'])}"
            )

    if has_failures:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command(name="explain")
def explain(
    rule_id: Annotated[
        str,
        typer.Argument(help="The ID of the rule to explain."),
    ],
) -> None:
    """Show detailed documentation and remediation steps for a rule.

    Examples:
        aegis explain allow_drop_table
        aegis explain allow_rename_table
    """
    config = load_config()
    normalized_rule_id = rule_id.lower().replace("-", "_")

    from aegis.rules.metadata import RULE_DOCUMENTATION

    if normalized_rule_id not in RULE_DOCUMENTATION:
        get_err_console().print(
            "[bold red]Error:[/bold red] Unknown rule "
            f"[yellow]'{escape(rule_id)}'[/yellow]"
        )
        raise typer.Exit(code=2)

    doc = RULE_DOCUMENTATION[normalized_rule_id]
    severity = config.severities.get(normalized_rule_id, doc["severity"])
    sev_color = "red" if severity.lower() == "error" else "yellow"

    panel_content = (
        f"[bold blue]Rule ID:[/bold blue] {normalized_rule_id}\n"
        f"[bold blue]Severity:[/bold blue] [{sev_color}]{severity}[/{sev_color}]\n\n"
        f"[bold]Description:[/bold]\n{doc['description']}\n\n"
        f"[bold]Why It Matters:[/bold]\n{doc['why_it_matters']}\n\n"
        f"[bold]Remediation:[/bold]\n{doc['remediation']}"
    )

    console.print(
        Panel(
            panel_content,
            title=f"[bold]Rule Documentation: {normalized_rule_id}[/bold]",
            title_align="left",
            border_style="blue",
            expand=False,
        )
    )
