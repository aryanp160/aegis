from typer.testing import CliRunner

from aegis import __version__
from aegis.cli import app

runner = CliRunner()


def test_version_command() -> None:
    """Verifies that running 'aegis version' prints the correct version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Aegis version" in result.stdout
    assert __version__ in result.stdout


def test_version_option() -> None:
    """Verifies that running 'aegis --version' prints the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Aegis version" in result.stdout
    assert __version__ in result.stdout


def test_help_option() -> None:
    """Verifies that running 'aegis --help' displays CLI help documentation."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Aegis: SQL Migration Static Analyzer." in result.stdout
