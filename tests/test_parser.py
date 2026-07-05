from pathlib import Path

import pytest
from sqlglot import exp

from aegis.parser.core import parse_migration
from aegis.parser.detector import detect_dialect
from aegis.parser.discovery import discover_migration_directories, discover_sql_files
from aegis.parser.exceptions import (
    DialectDetectionError,
    MigrationLoadError,
    SqlParseError,
)


def test_discover_sql_files(tmp_path: Path) -> None:
    """Verifies that discover_sql_files finds files in alphabetical order."""
    # Create nested directories
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    # Create SQL files out of order
    file_2 = dir_b / "0002_migration.sql"
    file_1 = dir_a / "0001_migration.sql"
    file_3 = tmp_path / "0003_migration.sql"
    file_ignored = dir_a / "README.md"

    file_2.touch()
    file_1.touch()
    file_3.touch()
    file_ignored.touch()

    sql_files = discover_sql_files(tmp_path)
    assert len(sql_files) == 3
    # Check alphabetized ordering by name
    assert sql_files[0].name == "0001_migration.sql"
    assert sql_files[1].name == "0002_migration.sql"
    assert sql_files[2].name == "0003_migration.sql"


def test_discover_migration_directories(tmp_path: Path) -> None:
    """Verifies that discover_migration_directories lists folders holding SQL files."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_c = tmp_path / "c"  # Holds no SQL files

    dir_a.mkdir()
    dir_b.mkdir()
    dir_c.mkdir()

    (dir_a / "0001.sql").touch()
    (dir_b / "0002.sql").touch()
    (dir_c / "readme.txt").touch()

    directories = discover_migration_directories(tmp_path)
    assert len(directories) == 2
    assert dir_a.resolve() in directories
    assert dir_b.resolve() in directories
    assert dir_c.resolve() not in directories


def test_detect_dialect_by_path() -> None:
    """Verifies dialect detection prioritizing path hints."""
    pg_path = Path("migrations/postgres/0001_init.sql")
    my_path = Path("migrations/mysql/0001_init.sql")
    assert detect_dialect("SELECT 1;", pg_path) == "postgres"
    assert (
        detect_dialect("SELECT 1;", Path("migrations/pg/0001_init.sql")) == "postgres"
    )
    assert detect_dialect("SELECT 1;", my_path) == "mysql"
    assert (
        detect_dialect("SELECT 1;", Path("migrations/my/0001_init.sql")) == "mysql"
    )


def test_detect_dialect_by_content() -> None:
    """Verifies dialect detection falls back to content regex scans."""
    # Postgres triggers
    assert detect_dialect("CREATE TABLE users (id SERIAL PRIMARY KEY);") == "postgres"
    assert (
        detect_dialect("CREATE TABLE users (id BIGSERIAL PRIMARY KEY);")
        == "postgres"
    )
    assert (
        detect_dialect("ALTER TABLE users ADD COLUMN created TIMESTAMPTZ;")
        == "postgres"
    )

    # MySQL triggers
    assert (
        detect_dialect("CREATE TABLE users (id INT AUTO_INCREMENT PRIMARY KEY);")
        == "mysql"
    )
    assert detect_dialect("CREATE TABLE users (id INT) ENGINE=InnoDB;") == "mysql"
    assert detect_dialect("SELECT * FROM `users`;") == "mysql"


def test_detect_dialect_ambiguous_raises_error() -> None:
    """Verifies that highly mixed keyword content triggers DialectDetectionError."""
    # Mixed triggers
    mixed_sql = "CREATE TABLE users (id SERIAL, count INT AUTO_INCREMENT);"
    with pytest.raises(DialectDetectionError) as exc_info:
        detect_dialect(mixed_sql)
    assert "SQL dialect could not be detected unambiguously" in str(exc_info.value)


def test_parse_migration_postgres_success(tmp_path: Path) -> None:
    """Verifies parsing of postgres migration file produces statements and AST nodes."""
    migration_file = tmp_path / "postgres_0001.sql"
    sql_content = """
    CREATE TABLE users (id SERIAL PRIMARY KEY);
    ALTER TABLE users ADD COLUMN age INT;
    """
    migration_file.write_text(sql_content, encoding="utf-8")

    parsed = parse_migration(migration_file, dialect_override="postgres")
    assert parsed.dialect == "postgres"
    assert len(parsed.statements) == 2
    assert len(parsed.ast_nodes) == 2

    assert isinstance(parsed.ast_nodes[0], exp.Create)
    assert isinstance(parsed.ast_nodes[1], exp.Alter)


def test_parse_migration_mysql_success(tmp_path: Path) -> None:
    """Verifies parsing of mysql migration file works."""
    migration_file = tmp_path / "mysql_0001.sql"
    sql_content = "CREATE TABLE `users` (id INT AUTO_INCREMENT) ENGINE=InnoDB;"
    migration_file.write_text(sql_content, encoding="utf-8")

    parsed = parse_migration(migration_file, dialect_override="mysql")
    assert parsed.dialect == "mysql"
    assert len(parsed.statements) == 1
    assert isinstance(parsed.ast_nodes[0], exp.Create)


def test_parse_migration_load_error_raises_exception() -> None:
    """Verifies loading a non-existent file raises MigrationLoadError."""
    with pytest.raises(MigrationLoadError) as exc_info:
        parse_migration(Path("non_existent_file.sql"))
    assert "Failed to read file" in str(exc_info.value)


def test_parse_migration_syntax_error_raises_exception(tmp_path: Path) -> None:
    """Verifies syntax errors in SQL compile to SqlParseError."""
    migration_file = tmp_path / "0001_bad.sql"
    migration_file.write_text("CREATE TABLE (id INT;", encoding="utf-8")

    with pytest.raises(SqlParseError) as exc_info:
        parse_migration(migration_file, dialect_override="postgres")
    assert "SQL syntax compilation error" in str(exc_info.value)
