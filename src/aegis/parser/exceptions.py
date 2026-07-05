class ParserError(Exception):
    """Base exception for all parsing and discovery-related errors in Aegis."""


class MigrationLoadError(ParserError):
    """Raised when migration files cannot be loaded due to file IO errors."""


class DialectDetectionError(ParserError):
    """Raised when SQL dialect detection fails or the dialect is unsupported."""


class SqlParseError(ParserError):
    """Raised when SQL parsing fails due to syntax or sqlglot compilation errors."""
