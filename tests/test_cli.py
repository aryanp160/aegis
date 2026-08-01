from pathlib import Path

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


def test_lint_valid_migration(tmp_path: Path) -> None:
    """Verifies that linting a valid SQL migration exits with code 0."""
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text(
        "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100));",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_lint_rule_violation(tmp_path: Path) -> None:
    """Verifies that linting a migration with a violation exits with code 1."""
    sql_file = tmp_path / "violation.sql"
    # By default allow_drop_table is False, so DROP TABLE is a violation
    sql_file.write_text("DROP TABLE users;", encoding="utf-8")
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 1
    assert "[allow_drop_table]" in result.stdout
    assert "Table deletion detected" in result.stdout


def test_lint_syntax_error(tmp_path: Path) -> None:
    """Verifies that linting a migration with syntax error exits with code 1."""
    sql_file = tmp_path / "bad.sql"
    sql_file.write_text("CREATE TABLE (id INT;", encoding="utf-8")
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 1
    assert "[syntax_error]" in result.stdout


def test_lint_non_existent_target() -> None:
    """Verifies that linting a non-existent path exits with code 2."""
    result = runner.invoke(app, ["lint", "non_existent_file.sql"])
    assert result.exit_code == 2
    assert "Error: Target path does not exist" in result.stdout


def test_lint_directory(tmp_path: Path) -> None:
    """Verifies that linting a directory containing violations exits with code 1."""
    # Create a subdir
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Valid file
    valid_file = migrations_dir / "0001_valid.sql"
    valid_file.write_text(
        "CREATE TABLE users (id SERIAL PRIMARY KEY);", encoding="utf-8"
    )

    # Invalid file
    invalid_file = migrations_dir / "0002_invalid.sql"
    invalid_file.write_text("DROP TABLE users;", encoding="utf-8")

    result = runner.invoke(app, ["lint", str(migrations_dir)])
    assert result.exit_code == 1
    assert "[allow_drop_table]" in result.stdout
    assert "[ERROR]" in result.stdout


def test_explain_valid_rule() -> None:
    """Verifies explaining a valid rule prints documentation."""
    result = runner.invoke(app, ["explain", "allow-drop-table"])
    assert result.exit_code == 0
    assert "Rule ID: allow_drop_table" in result.stdout
    assert "Description: Prohibits dropping tables" in result.stdout
    assert "Severity: error" in result.stdout
    assert "Why It Matters:" in result.stdout
    assert "Remediation:" in result.stdout


def test_explain_invalid_rule() -> None:
    """Verifies explaining an invalid rule prints an error and exits with 2."""
    result = runner.invoke(app, ["explain", "non-existent-rule"])
    assert result.exit_code == 2
    assert "Error: Unknown rule" in result.stdout
