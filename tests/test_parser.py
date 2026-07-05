import codecs
from pathlib import Path

import pytest
from pydantic import ValidationError

from aegis.parser import (
    BaseParser,
    FileDiscoveryError,
    InvalidSQLFileError,
    ParsedMigration,
    ParseFailure,
    ParserError,
    ParseResult,
    SQLDialect,
    UnsupportedDialectError,
    discover_migration_files,
    load_migration_file,
)


class MockParser(BaseParser):
    """A simple mock implementation of BaseParser for architectural testing."""

    def parse(self, file_path: Path) -> ParseResult:
        if not file_path.exists():
            return ParseResult(
                success=False,
                errors=["File does not exist"],
            )

        migration = ParsedMigration(
            path=file_path,
            dialect=SQLDialect.POSTGRESQL,
            raw_content="CREATE TABLE users (id INT);",
            statements=["CREATE TABLE users (id INT);"],
            ast_nodes=[],
        )
        return ParseResult(success=True, migration=migration)


def test_sql_dialect_enum_values() -> None:
    """Verifies defined SQLDialect enum values."""
    assert SQLDialect.POSTGRESQL.value == "postgresql"
    assert SQLDialect.MYSQL.value == "mysql"
    assert SQLDialect.UNKNOWN.value == "unknown"


def test_exception_inheritance() -> None:
    """Verifies that all custom parser exceptions inherit from ParserError."""
    assert issubclass(FileDiscoveryError, ParserError)
    assert issubclass(InvalidSQLFileError, ParserError)
    assert issubclass(UnsupportedDialectError, ParserError)
    assert issubclass(ParseFailure, ParserError)


def test_parsed_migration_validation() -> None:
    """Verifies that ParsedMigration correctly validates field constraints."""
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.MYSQL,
        raw_content="SELECT 1;",
        statements=["SELECT 1;"],
        ast_nodes=[],
    )
    assert migration.path == Path("migration.sql")
    assert migration.dialect == SQLDialect.MYSQL

    with pytest.raises(ValidationError):
        ParsedMigration(
            path=Path("migration.sql"),
            dialect="invalid_dialect",  # type: ignore
            raw_content="SELECT 1;",
        )


def test_parse_result_validation() -> None:
    """Verifies ParseResult schema validation."""
    result = ParseResult(success=True, errors=[])
    assert result.success is True
    assert result.migration is None


def test_mock_parser_contracts(tmp_path: Path) -> None:
    """Verifies the BaseParser interface contract works using MockParser."""
    parser = MockParser()

    fail_result = parser.parse(tmp_path / "missing.sql")
    assert fail_result.success is False
    assert "File does not exist" in fail_result.errors

    sql_file = tmp_path / "migration.sql"
    sql_file.write_text("CREATE TABLE users (id INT);", encoding="utf-8")

    success_result = parser.parse(sql_file)
    assert success_result.success is True
    assert success_result.migration is not None
    assert success_result.migration.dialect == SQLDialect.POSTGRESQL


def test_discover_migration_files_filters(tmp_path: Path) -> None:
    """Verifies discovery logic filters out ignored files and folders."""
    # Create subdirs
    normal_dir = tmp_path / "migrations"
    hidden_dir = tmp_path / ".hidden"
    pycache_dir = tmp_path / "__pycache__"

    for d in [normal_dir, hidden_dir, pycache_dir]:
        d.mkdir()

    # Create files
    sql_file_1 = normal_dir / "0002_migration.sql"
    sql_file_2 = normal_dir / "0001_migration.sql"
    txt_file = normal_dir / "readme.txt"
    hidden_sql = hidden_dir / "ignored.sql"
    pycache_sql = pycache_dir / "cached.sql"

    for f in [sql_file_1, sql_file_2, txt_file, hidden_sql, pycache_sql]:
        f.touch()

    # Discover files
    files = discover_migration_files(tmp_path)
    assert len(files) == 2
    # Check alphabetical ordering
    assert files[0].name == "0001_migration.sql"
    assert files[1].name == "0002_migration.sql"


def test_discover_migration_files_invalid_path() -> None:
    """Verifies discovery raises FileDiscoveryError on invalid/missing directories."""
    with pytest.raises(FileDiscoveryError):
        discover_migration_files(Path("/non_existent_directory_aegis"))


def test_load_migration_file_success(tmp_path: Path) -> None:
    """Verifies loading valid migration content and handling of BOM markers."""
    sql_file = tmp_path / "migration.sql"
    sql_content = "CREATE TABLE users (id INT);"

    # Write file with BOM marker
    with open(sql_file, mode="wb") as f:
        f.write(codecs.BOM_UTF8)
        f.write(sql_content.encode("utf-8"))

    parsed = load_migration_file(sql_file)
    assert parsed.path == sql_file.resolve()
    assert parsed.dialect == SQLDialect.UNKNOWN
    # Assert BOM is stripped
    assert parsed.raw_content == sql_content
    assert parsed.statements == []


def test_load_migration_file_failures(tmp_path: Path) -> None:
    """Verifies loader triggers InvalidSQLFileError on invalid parameters."""
    # File not found
    with pytest.raises(InvalidSQLFileError) as exc:
        load_migration_file(tmp_path / "missing_file.sql")
    assert "Migration file does not exist" in str(exc.value)

    # Empty file
    empty_file = tmp_path / "empty.sql"
    empty_file.touch()
    with pytest.raises(InvalidSQLFileError) as exc:
        load_migration_file(empty_file)
    assert "SQL migration file is empty" in str(exc.value)
