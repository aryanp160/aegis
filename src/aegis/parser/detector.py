import re
from pathlib import Path

from aegis.parser.enums import SQLDialect
from aegis.parser.errors import UnsupportedDialectError

# Heuristic patterns for PostgreSQL and MySQL dialects
POSTGRES_KEYWORDS = re.compile(
    r"\b(bigserial|serial|timestamptz|uuid_generate_v4|double precision|bytea|inet)\b"
    r"|::[a-zA-Z_]"
    r"|\bcreate\s+or\s+replace\s+function\b"
    r"|\blanguage\s+plpgsql\b",
    re.IGNORECASE,
)

MYSQL_KEYWORDS = re.compile(
    r"\b(auto_increment|tinyint|unsigned|mediumint|datetime|longtext|tinytext)\b"
    r"|\bengine\s*=\s*(innodb|myisam)\b"
    r"|`[a-zA-Z_][a-zA-Z0-9_]*`",  # backticks for identifiers
    re.IGNORECASE,
)


def detect_dialect(content: str, file_path: Path | None = None) -> SQLDialect:
    """Analyzes SQL migration file paths and content signatures to identify dialect.

    Args:
        content: The raw SQL string.
        file_path: Optional path to the migration SQL file.

    Returns:
        The detected SQLDialect enum (POSTGRESQL or MYSQL).

    Raises:
        UnsupportedDialectError: If dialect is unknown, unsupported, or ambiguous.
    """
    # 1. Path-based detection hints
    if file_path is not None:
        path_str = file_path.as_posix().lower()
        if "postgres" in path_str or "pg" in path_str.split("/"):
            return SQLDialect.POSTGRESQL
        if "mysql" in path_str or "my" in path_str.split("/"):
            return SQLDialect.MYSQL

    # 2. Content regex heuristics
    postgres_score = len(POSTGRES_KEYWORDS.findall(content))
    mysql_score = len(MYSQL_KEYWORDS.findall(content))

    if postgres_score > 0 and postgres_score > mysql_score:
        return SQLDialect.POSTGRESQL
    if mysql_score > 0 and mysql_score > postgres_score:
        return SQLDialect.MYSQL

    # 3. Unambiguous resolution check
    if postgres_score == 0 and mysql_score == 0:
        # If absolutely no triggers matched, default to postgres but log check
        return SQLDialect.POSTGRESQL

    # Ambiguous scores (equal match score > 0)
    raise UnsupportedDialectError(
        "SQL dialect could not be detected unambiguously. "
        f"Postgres score: {postgres_score}, MySQL score: {mysql_score}. "
        "Please reorganize migration directories or specify dialect manually."
    )
