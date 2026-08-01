import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from aegis import __version__
from aegis.config import load_config
from aegis.logging import setup_logging
from aegis.parser import SqlParser, discover_migration_files
from aegis.rules import check_rules

app = typer.Typer(
    name="aegis",
    help="Aegis: SQL Migration Static Analyzer.",
    no_args_is_help=True,
)
console = Console()
logger = logging.getLogger("aegis")


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


@app.command(name="lint")
def lint(
    targets: Annotated[
        list[Path],
        typer.Argument(help="One or more SQL migration files or directories to lint."),
    ],
) -> None:
    """Lint SQL migration files for rule violations."""
    files_to_lint: list[Path] = []
    for target in targets:
        if not target.exists():
            print(f"Error: Target path does not exist: {target}")
            raise typer.Exit(code=2)

        if target.is_file():
            files_to_lint.append(target)
        elif target.is_dir():
            try:
                files_to_lint.extend(discover_migration_files(target))
            except Exception as e:
                print(f"Error discovering files in {target}: {e}")
                raise typer.Exit(code=2) from e
        else:
            print(f"Error: Target path is not a file or directory: {target}")
            raise typer.Exit(code=2)

    parser = SqlParser()
    config = load_config()
    has_violations = False

    for file_path in files_to_lint:
        try:
            result = parser.parse(file_path)
            if not result.success:
                has_violations = True
                for err in result.errors:
                    print(f"{file_path}: [ERROR] [syntax_error] {err}")
            else:
                migration = result.migration
                if migration:
                    violations = check_rules(migration, config)
                    if violations:
                        has_violations = True
                        for v in violations:
                            print(
                                f"{v.file_path}: [{v.severity.upper()}] "
                                f"[{v.rule_name}] {v.message}"
                            )
        except Exception as e:
            print(f"Internal error processing {file_path}: {e}")
            raise typer.Exit(code=2) from e

    if has_violations:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command(name="explain")
def explain(
    rule_id: Annotated[
        str,
        typer.Argument(help="The ID of the rule to explain."),
    ],
) -> None:
    """Show detailed documentation and remediation steps for a rule."""
    config = load_config()
    normalized_rule_id = rule_id.lower().replace("-", "_")

    from aegis.rules.metadata import RULE_DOCUMENTATION

    if normalized_rule_id not in RULE_DOCUMENTATION:
        print(f"Error: Unknown rule '{rule_id}'")
        raise typer.Exit(code=2)

    doc = RULE_DOCUMENTATION[normalized_rule_id]
    severity = config.severities.get(normalized_rule_id, doc["severity"])

    print(f"Rule ID: {normalized_rule_id}")
    print(f"Description: {doc['description']}")
    print(f"Severity: {severity}")
    print("\nWhy It Matters:")
    print(doc["why_it_matters"])
    print("\nRemediation:")
    print(doc["remediation"])
