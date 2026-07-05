from enum import StrEnum


class SQLDialect(StrEnum):
    """Supported SQL dialects for static migration analysis."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    UNKNOWN = "unknown"
