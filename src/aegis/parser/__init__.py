from pathlib import Path

from aegis.parser.core import SqlParser
from aegis.parser.discovery import discover_migration_files
from aegis.parser.enums import SQLDialect
from aegis.parser.errors import (
    FileDiscoveryError,
    InvalidSQLFileError,
    ParseFailure,
    ParserError,
    UnsupportedDialectError,
)
from aegis.parser.interfaces import BaseParser
from aegis.parser.loader import load_migration_file
from aegis.parser.models import ParsedMigration, ParseResult

__all__ = [
    "SQLDialect",
    "BaseParser",
    "SqlParser",
    "ParsedMigration",
    "ParseResult",
    "ParserError",
    "FileDiscoveryError",
    "InvalidSQLFileError",
    "UnsupportedDialectError",
    "ParseFailure",
    "discover_migration_files",
    "load_migration_file",
    "parse",
    "parse_directory",
]


def parse(file_path: Path) -> ParseResult:
    """Convenience helper to parse a single migration SQL file."""
    return SqlParser().parse(file_path)


def parse_directory(directory_path: Path) -> list[ParseResult]:
    """Convenience helper to parse all migration files recursively in a directory."""
    return SqlParser().parse_directory(directory_path)
