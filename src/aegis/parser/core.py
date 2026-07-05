import logging
from pathlib import Path
from typing import cast

import sqlglot
from sqlglot.expressions import Expression

from aegis.parser.detector import detect_dialect
from aegis.parser.exceptions import MigrationLoadError, SqlParseError
from aegis.parser.models import ParsedMigration

logger = logging.getLogger("aegis.parser")


def parse_migration(
    file_path: Path, dialect_override: str | None = None
) -> ParsedMigration:
    """Loads a SQL migration file, detects its dialect, and parses it into AST nodes.

    Args:
        file_path: Path to the migration SQL file.
        dialect_override: Option to explicitly set dialect ("postgres" or "mysql").

    Returns:
        ParsedMigration model containing details and AST nodes.

    Raises:
        MigrationLoadError: If the file cannot be read.
        DialectDetectionError: If dialect is ambiguous.
        SqlParseError: If SQL parsing fails.
    """
    logger.debug("Loading migration file: %s", file_path)
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise MigrationLoadError(f"Failed to read file {file_path}: {e}") from e

    # Detect dialect
    dialect = dialect_override
    if not dialect:
        dialect = detect_dialect(content, file_path)
    logger.debug("Detected dialect for %s: %s", file_path, dialect)

    # Parse using sqlglot
    try:
        # sqlglot.parse parses all statements in the text and
        # returns a list of Expression nodes
        ast_nodes = cast(
            list[Expression],
            [
                node
                for node in sqlglot.parse(content, read=dialect)
                if node is not None
            ],
        )
    except sqlglot.errors.ParseError as e:
        raise SqlParseError(f"SQL syntax compilation error in {file_path}: {e}") from e
    except Exception as e:
        raise SqlParseError(f"Failed to parse SQL in {file_path}: {e}") from e

    # Extract individual SQL statements (stripping comments and whitespaces)
    # sqlglot expressions compile back to raw SQL via expression.sql()
    statements = [node.sql(dialect=dialect) for node in ast_nodes if node is not None]

    return ParsedMigration(
        path=file_path.resolve(),
        dialect=dialect,
        raw_content=content,
        statements=statements,
        ast_nodes=ast_nodes,
    )
