import logging

import typer
from rich.console import Console

from aegis import __version__
from aegis.logging import setup_logging

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
