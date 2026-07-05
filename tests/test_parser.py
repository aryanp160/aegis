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
    # Test valid model
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.MYSQL,
        raw_content="SELECT 1;",
        statements=["SELECT 1;"],
        ast_nodes=[],
    )
    assert migration.path == Path("migration.sql")
    assert migration.dialect == SQLDialect.MYSQL

    # Test invalid dialect type
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

    # Test failure case
    fail_result = parser.parse(tmp_path / "missing.sql")
    assert fail_result.success is False
    assert "File does not exist" in fail_result.errors

    # Test success case
    sql_file = tmp_path / "migration.sql"
    sql_file.write_text("CREATE TABLE users (id INT);", encoding="utf-8")

    success_result = parser.parse(sql_file)
    assert success_result.success is True
    assert success_result.migration is not None
    assert success_result.migration.dialect == SQLDialect.POSTGRESQL
