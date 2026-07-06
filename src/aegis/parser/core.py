import logging
from pathlib import Path
from typing import cast

import sqlglot
from sqlglot.expressions import Expression

from aegis.parser.detector import detect_dialect
from aegis.parser.discovery import discover_migration_files
from aegis.parser.enums import SQLDialect
from aegis.parser.errors import ParseFailure, ParserError
from aegis.parser.interfaces import BaseParser
from aegis.parser.loader import load_migration_file
from aegis.parser.models import ParseResult

logger = logging.getLogger("aegis.parser.core")


class SqlParser(BaseParser):
    """Concrete SQL parser parsing PostgreSQL and MySQL migrations using sqlglot."""

    def parse(self, file_path: Path) -> ParseResult:
        """Parses a single SQL migration file into a ParseResult.

        Args:
            file_path: The Path to the migration SQL file.

        Returns:
            A ParseResult containing success state, ParsedMigration, or errors.
        """
        try:
            # 1. Load the raw migration file
            parsed_migration = load_migration_file(file_path)

            # 2. Detect dialect
            dialect = detect_dialect(parsed_migration.raw_content, file_path)
            parsed_migration.dialect = dialect

            # 3. Parse SQL using sqlglot
            # Map SQLDialect enum to sqlglot read dialect name
            glot_dialect = "postgres" if dialect == SQLDialect.POSTGRESQL else "mysql"

            try:
                # Compile AST nodes
                nodes = sqlglot.parse(parsed_migration.raw_content, read=glot_dialect)
                ast_nodes = cast(
                    list[Expression], [node for node in nodes if node is not None]
                )
            except sqlglot.errors.ParseError as e:
                # Compile detailed line and column diagnostics from sqlglot errors
                diag_messages = []
                for error in e.errors:
                    line = error.get("line")
                    col = error.get("col")
                    description = error.get("description")
                    diag_messages.append(f"Line {line}, Col {col}: {description}")

                if diag_messages:
                    err_msg = "SQL syntax compile failure:\n" + "\n".join(diag_messages)
                else:
                    err_msg = f"SQL syntax compile failure: {e}"

                raise ParseFailure(err_msg) from e
            except Exception as e:
                raise ParseFailure(f"Failed to parse SQL content: {e}") from e

            # 4. Generate clean statements lists
            statements = [node.sql(dialect=glot_dialect) for node in ast_nodes]

            parsed_migration.statements = statements
            parsed_migration.ast_nodes = ast_nodes

            return ParseResult(success=True, migration=parsed_migration)

        except ParserError as e:
            logger.error("Parser failed on file %s: %s", file_path, e)
            return ParseResult(success=False, errors=[str(e)])
        except Exception as e:
            logger.error("Unexpected failure on file %s: %s", file_path, e)
            return ParseResult(success=False, errors=[f"Unexpected error: {e}"])

    def parse_directory(self, directory_path: Path) -> list[ParseResult]:
        """Discovers and parses all SQL migration files recursively in the directory.

        Args:
            directory_path: The directory path to scan.

        Returns:
            List of ParseResult objects.
        """
        results: list[ParseResult] = []
        try:
            sql_files = discover_migration_files(directory_path)
        except ParserError as e:
            logger.error("Failed to discover files in %s: %s", directory_path, e)
            return [ParseResult(success=False, errors=[str(e)])]

        for file in sql_files:
            results.append(self.parse(file))

        return results
