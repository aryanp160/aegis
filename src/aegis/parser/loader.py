import logging
import re
from pathlib import Path

from aegis.parser.enums import SQLDialect
from aegis.parser.errors import EmptySQLFileError, UnreadableFileError
from aegis.parser.models import ParsedMigration

logger = logging.getLogger("aegis.parser.loader")


def is_empty_sql(content: str) -> bool:
    """Helper to detect if SQL content contains only comments and whitespaces."""
    # Remove single line comments starting with --
    content_no_comments = re.sub(r"--.*$", "", content, flags=re.MULTILINE)
    # Remove block comments /* ... */
    content_no_comments = re.sub(r"/\*.*?\*/", "", content_no_comments, flags=re.DOTALL)
    return not content_no_comments.strip()


def load_migration_file(file_path: Path) -> ParsedMigration:
    """Reads a SQL migration file and returns a ParsedMigration object.

    Handles UTF-8 encoding and strips Byte Order Marks (BOM) automatically.

    Args:
        file_path: Path to the SQL file.

    Returns:
        A ParsedMigration containing path metadata and raw SQL content.

    Raises:
        UnreadableFileError: If the file is missing, a directory, or fails to read.
        EmptySQLFileError: If the file is empty or contains only comments.
    """
    logger.info("Loading SQL migration file: %s", file_path)

    # 1. Path validations
    if not file_path.is_file():
        raise UnreadableFileError(
            f"Migration file does not exist or is not a file: {file_path}"
        )

    # 2. Content reading (with UTF-8 and BOM signature handling)
    try:
        with open(file_path, encoding="utf-8-sig") as f:
            content = f.read()
    except Exception as e:
        raise UnreadableFileError(f"Failed to read file {file_path}: {e}") from e

    # 3. Content emptiness/comments validation
    if is_empty_sql(content):
        raise EmptySQLFileError(
            f"SQL migration file contains no executable SQL: {file_path}"
        )

    # 4. ParsedMigration construction (ast_nodes and statements remain empty for now)
    return ParsedMigration(
        path=file_path.resolve(),
        dialect=SQLDialect.UNKNOWN,
        raw_content=content,
        statements=[],
        ast_nodes=[],
    )
