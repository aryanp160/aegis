from pathlib import Path

from typer.testing import CliRunner

from aegis import __version__
from aegis.cli import app

runner = CliRunner()


def test_version_command() -> None:
    """Verifies that running 'aegis version' prints the correct version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Aegis Version" in result.stdout
    assert __version__ in result.stdout


def test_version_option() -> None:
    """Verifies that running 'aegis --version' prints the correct version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Aegis Version" in result.stdout
    assert __version__ in result.stdout


def test_help_option() -> None:
    """Verifies that running 'aegis --help' displays CLI help documentation."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Aegis" in result.stdout
    assert "static analyzer for Python SQL migrations" in result.stdout


def test_lint_valid_migration(tmp_path: Path) -> None:
    """Verifies that linting a valid SQL migration exits with code 0."""
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text(
        "SET lock_timeout = '2s';\n"
        "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 0
    assert result.stdout.strip() == ""


def test_lint_rule_violation(tmp_path: Path) -> None:
    """Verifies that linting a migration with a violation exits with code 1."""
    sql_file = tmp_path / "violation.sql"
    # By default allow_drop_table (AEG-107) is False, so DROP TABLE is a violation
    sql_file.write_text("DROP TABLE users;", encoding="utf-8")
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 1
    assert "AEG-107" in result.stdout
    assert "DROP TABLE / DROP COLUMN protection" in result.stdout


def test_lint_syntax_error(tmp_path: Path) -> None:
    """Verifies that linting a migration with syntax error exits with code 1."""
    sql_file = tmp_path / "bad.sql"
    sql_file.write_text("CREATE TABLE (id INT;", encoding="utf-8")
    result = runner.invoke(app, ["lint", str(sql_file)])
    assert result.exit_code == 1
    assert "syntax_error" in result.stdout


def test_lint_non_existent_target() -> None:
    """Verifies that linting a non-existent path exits with code 2."""
    result = runner.invoke(app, ["lint", "non_existent_file.sql"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Error: Target path does not exist" in output


def test_lint_directory(tmp_path: Path) -> None:
    """Verifies that linting a directory containing violations exits with code 1."""
    # Create a subdir
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Valid file
    valid_file = migrations_dir / "0001_valid.sql"
    valid_file.write_text(
        "CREATE TABLE users (id INT PRIMARY KEY);", encoding="utf-8"
    )

    # Invalid file
    invalid_file = migrations_dir / "0002_invalid.sql"
    invalid_file.write_text("DROP TABLE users;", encoding="utf-8")

    result = runner.invoke(app, ["lint", str(migrations_dir)])
    assert result.exit_code == 1
    assert "AEG-107" in result.stdout
    assert "ERROR" in result.stdout or "ERROR" in result.stderr


def test_explain_valid_rule() -> None:
    """Verifies explaining a valid rule prints documentation."""
    result = runner.invoke(app, ["explain", "AEG-107"])
    assert result.exit_code == 0
    assert "AEG-107" in result.stdout
    assert "Description" in result.stdout
    assert "Protects against destructive drops" in result.stdout
    assert "Severity" in result.stdout
    assert "Why It Matters" in result.stdout
    assert "Remediation" in result.stdout


def test_explain_rule_by_name() -> None:
    """Verifies explaining a rule by its name (allow_drop_table)."""
    result = runner.invoke(app, ["explain", "allow_drop_table"])
    assert result.exit_code == 0
    assert "AEG-107" in result.stdout


def test_explain_invalid_rule() -> None:
    """Verifies explaining an invalid rule prints an error and exits with 2."""
    result = runner.invoke(app, ["explain", "non-existent-rule"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Error: Unknown rule" in output


def test_rules_command() -> None:
    """Verifies that running 'aegis rules' lists registered rules in catalog table."""
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    assert "Aegis Static Analysis Rules Catalog" in result.stdout
    assert "AEG-101" in result.stdout
    assert "AEG-107" in result.stdout
    assert "Displayed" in result.stdout


def test_rules_category_filter() -> None:
    """Verifies that 'aegis rules --category destructive' filters by category."""
    result = runner.invoke(app, ["rules", "--category", "destructive"])
    assert result.exit_code == 0
    assert "AEG-101" in result.stdout
    assert "Destructive" in result.stdout


def test_rules_severity_filter() -> None:
    """Verifies that 'aegis rules --severity error' filters by severity."""
    result = runner.invoke(app, ["rules", "--severity", "error"])
    assert result.exit_code == 0
    assert "ERROR" in result.stdout


def test_rules_invalid_category() -> None:
    """Verifies that 'aegis rules --category invalid' exits with code 2."""
    result = runner.invoke(app, ["rules", "--category", "invalid_cat"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Invalid category filter" in output


def test_rules_invalid_severity() -> None:
    """Verifies that 'aegis rules --severity invalid' exits with code 2."""
    result = runner.invoke(app, ["rules", "--severity", "invalid_sev"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Invalid severity filter" in output


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
    assert data["summary"]["violations_count"] >= 1
    assert data["summary"]["success"] is False
    assert len(data["violations"]) >= 1
    assert data["violations"][0]["rule"] == "AEG-107"
    assert data["violations"][0]["severity"] == "error"


def test_lint_severity_filtering(tmp_path: Path) -> None:
    """Verifies that '--severity' filters out lower severity warnings/infos."""
    sql_file = tmp_path / "test.sql"
    # This migration has an error (AEG-107 DROP TABLE)
    # and a warning (AEG-109 missing lock timeout)
    sql_file.write_text("DROP TABLE logs;", encoding="utf-8")

    # Run with default (warning & error shown)
    result_all = runner.invoke(app, ["lint", str(sql_file), "--format", "json"])
    import json

    data_all = json.loads(result_all.stdout)
    assert data_all["summary"]["violations_count"] >= 2

    # Run with --severity error. Warning (AEG-109) should be filtered
    # out, leaving error (AEG-107).
    result_err = runner.invoke(
        app,
        ["lint", str(sql_file), "--format", "json", "--severity", "error"],
    )
    data_err = json.loads(result_err.stdout)
    assert data_err["summary"]["violations_count"] == 1
    assert data_err["violations"][0]["rule"] == "AEG-107"


def test_lint_ignore_suppression(tmp_path: Path) -> None:
    """Verifies that '--ignore' suppresses designated rules."""
    sql_file = tmp_path / "violation.sql"
    sql_file.write_text("DROP TABLE users;", encoding="utf-8")

    # Lint with ignore option
    result = runner.invoke(
        app,
        ["lint", str(sql_file), "--format", "json", "--ignore", "AEG-107,AEG-109"],
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
    assert data["summary"]["violations_count"] >= 1
    assert Path(data["violations"][0]["file"]).name == "0001_init.sql"


def test_lint_no_targets() -> None:
    """Verifies that linting with no targets provided prints error and exits with 2."""
    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "No targets specified" in output


def test_lint_invalid_format() -> None:
    """Verifies that linting with an invalid format prints error and exits with 2."""
    result = runner.invoke(app, ["lint", "dummy.sql", "--format", "xml"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Invalid format option" in output


def test_lint_invalid_severity() -> None:
    """Verifies linting with an invalid severity level exits with 2."""
    result = runner.invoke(app, ["lint", "dummy.sql", "--severity", "critical"])
    assert result.exit_code == 2
    output = result.stdout + result.stderr
    assert "Invalid severity level" in output
