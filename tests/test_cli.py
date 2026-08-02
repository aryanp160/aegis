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


def test_lint_format_json(tmp_path: Path) -> None:
    """Verifies that linting with '--format json' outputs valid JSON schema."""
    sql_file = tmp_path / "violation.sql"
    sql_file.write_text("DROP TABLE users;", encoding="utf-8")
    result = runner.invoke(app, ["lint", str(sql_file), "--format", "json"])
    assert result.exit_code == 1

    import json

    data = json.loads(result.stdout)
    assert "metadata" in data
    assert "version" in data["metadata"]
    assert "timestamp" in data["metadata"]
    assert data["summary"]["files_scanned"] == 1
    assert data["summary"]["violations_count"] == 1
    assert data["summary"]["success"] is False
    assert len(data["violations"]) == 1
    assert data["violations"][0]["rule"] == "allow_drop_table"
    assert data["violations"][0]["severity"] == "error"


def test_lint_severity_filtering(tmp_path: Path) -> None:
    """Verifies that '--severity error' filters out lower severity warnings."""
    # Create file with both a warning (rename table) and an error (drop table).
    # To test a warning, write a custom config with allow_rename_table = False
    # and allow_drop_table = False.
    config_file = tmp_path / "aegis.toml"
    config_file.write_text(
        """
[rules]
allow_rename_table = false
allow_drop_table = false
""",
        encoding="utf-8",
    )

    sql_file = tmp_path / "test.sql"
    sql_file.write_text(
        "ALTER TABLE users RENAME TO customers; DROP TABLE logs;",
        encoding="utf-8",
    )

    # Run with default (warning & error shown)
    # Pass the start_path by placing us in that directory
    result_all = runner.invoke(
        app, ["lint", str(sql_file), "--format", "json"], env={"COV_CORE_SOURCE": ""}
    )
    import json

    # We need to load config in target directory, so we change CWD to tmp_path
    # so that the configuration file is automatically discovered.
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result_all = runner.invoke(app, ["lint", "test.sql", "--format", "json"])
        data_all = json.loads(result_all.stdout)
        assert data_all["summary"]["violations_count"] == 2

        # Run with --severity error. Warning should be filtered out.
        result_err = runner.invoke(
            app,
            ["lint", "test.sql", "--format", "json", "--severity", "error"],
        )
        data_err = json.loads(result_err.stdout)
        assert data_err["summary"]["violations_count"] == 1
        assert data_err["violations"][0]["rule"] == "allow_drop_table"
    finally:
        os.chdir(old_cwd)


def test_lint_ignore_suppression(tmp_path: Path) -> None:
    """Verifies that '--ignore' suppresses designated rules."""
    sql_file = tmp_path / "violation.sql"
    sql_file.write_text("DROP TABLE users;", encoding="utf-8")

    # Lint with ignore option
    result = runner.invoke(
        app,
        ["lint", str(sql_file), "--format", "json", "--ignore", "allow_drop_table"],
    )
    assert result.exit_code == 0
    import json

    data = json.loads(result.stdout)
    assert data["summary"]["violations_count"] == 0
    assert data["summary"]["success"] is True


def test_lint_exclude_paths(tmp_path: Path) -> None:
    """Verifies that '--exclude' skips designated directories or files."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create normal file
    f1 = migrations_dir / "0001_init.sql"
    f1.write_text("DROP TABLE users;", encoding="utf-8")

    # Create file to exclude
    f2 = migrations_dir / "0002_ignored.sql"
    f2.write_text("DROP TABLE users;", encoding="utf-8")

    # Run lint excluding f2
    result = runner.invoke(
        app,
        ["lint", str(migrations_dir), "--format", "json", "--exclude", str(f2)],
    )
    assert result.exit_code == 1
    import json

    data = json.loads(result.stdout)
    assert data["summary"]["files_scanned"] == 1
    assert data["summary"]["violations_count"] == 1
    assert Path(data["violations"][0]["file"]).name == "0001_init.sql"
