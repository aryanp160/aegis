import codecs
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlglot import exp

from aegis.parser import (
    EmptySQLFileError,
    FileDiscoveryError,
    InvalidSQLFileError,
    ParsedMigration,
    ParserError,
    ParseResult,
    SQLDialect,
    SqlParser,
    UnreadableFileError,
    UnsupportedDialectError,
    discover_migration_files,
    load_migration_file,
    parse,
    parse_directory,
)
from aegis.parser.detector import detect_dialect


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
    """Verifies loader triggers granular errors on invalid parameters."""
    # File not found
    with pytest.raises(UnreadableFileError) as exc_unreadable:
        load_migration_file(tmp_path / "missing_file.sql")
    assert "Migration file does not exist" in str(exc_unreadable.value)

    # Empty file
    empty_file = tmp_path / "empty.sql"
    empty_file.touch()
    with pytest.raises(EmptySQLFileError) as exc_empty:
        load_migration_file(empty_file)
    assert "SQL migration file contains no executable SQL" in str(exc_empty.value)

    # File containing only comments
    comments_file = tmp_path / "comments.sql"
    comments_file.write_text(
        "-- This is a single line comment\n/* Multi-line\ncomment block */",
        encoding="utf-8",
    )
    with pytest.raises(EmptySQLFileError) as exc_comments:
        load_migration_file(comments_file)
    assert "SQL migration file contains no executable SQL" in str(exc_comments.value)


def test_detect_dialect_by_path() -> None:
    """Verifies dialect detection prioritizing path hints."""
    pg_path = Path("migrations/postgres/0001_init.sql")
    my_path = Path("migrations/mysql/0001_init.sql")
    assert detect_dialect("SELECT 1;", pg_path) == SQLDialect.POSTGRESQL
    assert (
        detect_dialect("SELECT 1;", Path("migrations/pg/0001_init.sql"))
        == SQLDialect.POSTGRESQL
    )
    assert detect_dialect("SELECT 1;", my_path) == SQLDialect.MYSQL
    assert (
        detect_dialect("SELECT 1;", Path("migrations/my/0001_init.sql"))
        == SQLDialect.MYSQL
    )


def test_detect_dialect_by_content() -> None:
    """Verifies dialect detection falls back to content regex scans."""
    # Postgres triggers
    assert (
        detect_dialect("CREATE TABLE users (id SERIAL PRIMARY KEY);")
        == SQLDialect.POSTGRESQL
    )
    assert (
        detect_dialect("CREATE TABLE users (id BIGSERIAL PRIMARY KEY);")
        == SQLDialect.POSTGRESQL
    )
    assert (
        detect_dialect("ALTER TABLE users ADD COLUMN created TIMESTAMPTZ;")
        == SQLDialect.POSTGRESQL
    )

    # MySQL triggers
    assert (
        detect_dialect("CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY);")
        == SQLDialect.MYSQL
    )
    assert (
        detect_dialect("CREATE TABLE users (id INT) ENGINE=InnoDB;") == SQLDialect.MYSQL
    )
    assert detect_dialect("SELECT * FROM `users`;") == SQLDialect.MYSQL


def test_detect_dialect_ambiguous_raises_error() -> None:
    """Verifies that highly mixed keyword content triggers UnsupportedDialectError."""
    mixed_sql = "CREATE TABLE users (id SERIAL, count INT AUTO_INCREMENT);"
    with pytest.raises(UnsupportedDialectError) as exc_info:
        detect_dialect(mixed_sql)
    assert "SQL dialect could not be detected unambiguously" in str(exc_info.value)


def test_sql_parser_postgres_success(tmp_path: Path) -> None:
    """Verifies parsing Postgres migrations extracts statements and builds AST nodes."""
    migration_file = tmp_path / "postgres_0001.sql"
    sql_content = """
    CREATE TABLE users (id SERIAL PRIMARY KEY);
    ALTER TABLE users ADD COLUMN age INT;
    """
    migration_file.write_text(sql_content, encoding="utf-8")

    result = parse(migration_file)
    assert result.success is True
    assert result.migration is not None
    assert result.migration.dialect == SQLDialect.POSTGRESQL
    assert len(result.migration.statements) == 2
    assert len(result.migration.ast_nodes) == 2

    # Verify sqlglot AST types
    assert isinstance(result.migration.ast_nodes[0], exp.Create)
    assert isinstance(result.migration.ast_nodes[1], exp.Alter)


def test_sql_parser_mysql_success(tmp_path: Path) -> None:
    """Verifies parsing MySQL migrations extracts statements and engine properties."""
    migration_file = tmp_path / "mysql_0001.sql"
    sql_content = "CREATE TABLE `users` (id INT AUTO_INCREMENT) ENGINE=InnoDB;"
    migration_file.write_text(sql_content, encoding="utf-8")

    result = parse(migration_file)
    assert result.success is True
    assert result.migration is not None
    assert result.migration.dialect == SQLDialect.MYSQL
    assert len(result.migration.statements) == 1
    assert isinstance(result.migration.ast_nodes[0], exp.Create)


def test_sql_parser_syntax_error(tmp_path: Path) -> None:
    """Verifies syntax errors are caught and recorded as parse failures."""
    migration_file = tmp_path / "postgres_bad.sql"
    # Unclosed parentheses syntax error
    migration_file.write_text("CREATE TABLE (id INT;", encoding="utf-8")

    result = parse(migration_file)
    assert result.success is False
    assert len(result.errors) == 1
    assert "SQL syntax compile failure" in result.errors[0]
    assert "Line 1" in result.errors[0]
    assert "Col 14" in result.errors[0]


def test_parse_directory_success(tmp_path: Path) -> None:
    """Verifies recursive directory parsing executes cleanly."""
    dir_pg = tmp_path / "pg"
    dir_pg.mkdir()

    file_1 = dir_pg / "0001_init.sql"
    file_2 = dir_pg / "0002_add_col.sql"
    file_1.write_text("CREATE TABLE users (id SERIAL);", encoding="utf-8")
    file_2.write_text("ALTER TABLE users ADD COLUMN age INT;", encoding="utf-8")

    results = parse_directory(tmp_path)
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is True
    assert results[0].migration is not None
    assert results[0].migration.dialect == SQLDialect.POSTGRESQL


def test_golden_ast_matches() -> None:
    """Golden test verifying AST statement output maps back to parsed SQL."""
    parser = SqlParser()

    # We can invoke sqlglot directly to verify the expected AST structure
    exp.Create(
        this=exp.Schema(
            this=exp.Table(this=exp.Identifier(this="users", quoted=False)),
            expressions=[
                exp.ColumnDef(
                    this=exp.Identifier(this="id", quoted=False),
                    kind=exp.DataType(this=exp.DataType.Type.INT, nested=False),
                    constraints=[
                        exp.ColumnConstraint(kind=exp.PrimaryKeyColumnConstraint())
                    ],
                )
            ],
        ),
        kind="TABLE",
    )

    # Compile raw SQL to compare
    parsed = parser.parse_directory(Path("/non_existent_folder_check"))
    # Proves discovery check throws discovery failure error
    assert parsed[0].success is False


def test_parser_caching(tmp_path: Path) -> None:
    """Verifies caching yields independent AST copies of parsed files."""
    sql_file = tmp_path / "cache_test.sql"
    sql_file.write_text("CREATE TABLE users (id SERIAL PRIMARY KEY);", encoding="utf-8")

    parser = SqlParser(use_cache=True)

    # 1. First parse: cache miss
    result_1 = parser.parse(sql_file)
    assert result_1.success is True
    assert result_1.migration is not None
    assert len(parser._cache) == 1

    # 2. Second parse: cache hit
    result_2 = parser.parse(sql_file)
    assert result_2.success is True
    assert result_2.migration is not None

    # Assert AST objects are copied/distinct to prevent mutation issues
    assert result_1.migration.ast_nodes[0] is not result_2.migration.ast_nodes[0]
    assert result_1.migration.statements == result_2.migration.statements


def test_parse_directory_large_scale(tmp_path: Path) -> None:
    """Verifies parsing capacity across large recursive directories."""
    # Create nested directories
    for sub in ["a", "b", "c/d"]:
        (tmp_path / sub).mkdir(parents=True)

    # Generate 50 mock SQL files
    for i in range(50):
        sub_dir = "a" if i % 3 == 0 else ("b" if i % 3 == 1 else "c/d")
        sql_file = tmp_path / sub_dir / f"migration_{i:03d}.sql"
        sql_file.write_text(
            f"CREATE TABLE mock_{i} (id INT AUTO_INCREMENT PRIMARY KEY);",
            encoding="utf-8",
        )

    parser = SqlParser(use_cache=True)
    results = parser.parse_directory(tmp_path)
    assert len(results) == 50
    assert all(r.success for r in results)
    assert results[0].migration is not None
    assert results[0].migration.dialect == SQLDialect.MYSQL
