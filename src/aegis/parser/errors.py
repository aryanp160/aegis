class ParserError(Exception):
    """Base exception for all parsing and discovery-related errors in Aegis."""


class FileDiscoveryError(ParserError):
    """Raised when migration files or directories cannot be discovered."""


class InvalidSQLFileError(ParserError):
    """Raised when a SQL migration file is empty, missing, or unreadable."""


class UnsupportedDialectError(ParserError):
    """Raised when the detected or specified SQL dialect is not supported."""


class ParseFailure(ParserError):
    """Raised when parsing of SQL statements fails."""
