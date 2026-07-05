import re
from pathlib import Path

from aegis.parser.exceptions import DialectDetectionError

# Detection patterns based on keywords and syntax patterns
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


def detect_dialect(content: str, file_path: Path | None = None) -> str:
    """Detects if SQL content belongs to postgres or mysql dialect.

    Checks file path name hints first, then falls back to content regex analysis.

    Args:
        content: The raw SQL query string.
        file_path: Optional path to the SQL file to extract naming hints.

    Returns:
        Detected dialect string: "postgres" or "mysql".

    Raises:
        DialectDetectionError: If detection is ambiguous or dialect is unsupported.
    """
    # 1. Path-based detection hints
    if file_path is not None:
        path_str = file_path.as_posix().lower()
        if "postgres" in path_str or "pg" in path_str.split("/"):
            return "postgres"
        if "mysql" in path_str or "my" in path_str.split("/"):
            return "mysql"

    # 2. Content regex heuristics
    postgres_score = len(POSTGRES_KEYWORDS.findall(content))
    mysql_score = len(MYSQL_KEYWORDS.findall(content))

    if postgres_score > 0 and postgres_score > mysql_score:
        return "postgres"
    if mysql_score > 0 and mysql_score > postgres_score:
        return "mysql"

    # Default fallback or raising error if absolutely ambiguous
    if postgres_score == 0 and mysql_score == 0:
        # Fallback to postgres as a sensible default, but logging warning
        return "postgres"

    raise DialectDetectionError(
        "SQL dialect could not be detected unambiguously. "
        f"Postgres match count: {postgres_score}, MySQL match count: {mysql_score}. "
        "Please specify dialect in configuration or file path naming structure."
    )
