import logging
from pathlib import Path

from aegis.parser.enums import SQLDialect
from aegis.parser.errors import InvalidSQLFileError
from aegis.parser.models import ParsedMigration

logger = logging.getLogger("aegis.parser.loader")


def load_migration_file(file_path: Path) -> ParsedMigration:
    """Reads a SQL migration file and returns a ParsedMigration object.

    Handles UTF-8 encoding and strips Byte Order Marks (BOM) automatically.

    Args:
        file_path: Path to the SQL file.

    Returns:
        A ParsedMigration containing path metadata and raw SQL content.

    Raises:
        InvalidSQLFileError: If the file is unreadable, missing, or empty.
    """
    logger.info("Loading SQL migration file: %s", file_path)

    # 1. Path validations
    if not file_path.is_file():
        raise InvalidSQLFileError(f"Migration file does not exist: {file_path}")

    # 2. Content reading (with UTF-8 and BOM signature handling)
    try:
        with open(file_path, encoding="utf-8-sig") as f:
            content = f.read()
    except Exception as e:
        raise InvalidSQLFileError(f"Failed to read file {file_path}: {e}") from e

    # 3. Size validation
    if not content.strip():
        raise InvalidSQLFileError(f"SQL migration file is empty: {file_path}")

    # 4. ParsedMigration construction (ast_nodes and statements remain empty for now)
    return ParsedMigration(
        path=file_path.resolve(),
        dialect=SQLDialect.UNKNOWN,
        raw_content=content,
        statements=[],
        ast_nodes=[],
    )
