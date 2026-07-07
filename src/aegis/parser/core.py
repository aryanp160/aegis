import logging
import time
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

    def __init__(self, use_cache: bool = True) -> None:
        """Initializes the SqlParser.

        Args:
            use_cache: If True, enables caching of parsed statements and AST nodes.
        """
        self.use_cache = use_cache
        # Cache mapping: (content_hash, dialect) -> (statements, ast_nodes)
        self._cache: dict[
            tuple[int, SQLDialect], tuple[list[str], list[Expression]]
        ] = {}

    def parse(self, file_path: Path) -> ParseResult:
        """Parses a single SQL migration file into a ParseResult.

        Args:
            file_path: The Path to the migration SQL file.

        Returns:
            A ParseResult containing success state, ParsedMigration, or errors.
        """
        start_time = time.perf_counter()
        try:
            # 1. Load the raw migration file
            parsed_migration = load_migration_file(file_path)

            # 2. Detect dialect
            dialect = detect_dialect(parsed_migration.raw_content, file_path)
            parsed_migration.dialect = dialect

            # 3. Cache lookup
            cache_key = (hash(parsed_migration.raw_content), dialect)
            if self.use_cache and cache_key in self._cache:
                logger.debug("Cache hit for file: %s", file_path)
                cached_statements, cached_ast = self._cache[cache_key]
                parsed_migration.statements = cached_statements.copy()
                parsed_migration.ast_nodes = [node.copy() for node in cached_ast]
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "Parsed file %s (cached) in %.2f ms", file_path, duration_ms
                )
                return ParseResult(success=True, migration=parsed_migration)

            # 4. Parse SQL using sqlglot
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

            # 5. Generate clean statements lists
            statements = [node.sql(dialect=glot_dialect) for node in ast_nodes]

            parsed_migration.statements = statements
            parsed_migration.ast_nodes = ast_nodes

            # 6. Cache save
            if self.use_cache:
                self._cache[cache_key] = (statements, ast_nodes)

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Parsed file %s in %.2f ms", file_path, duration_ms)

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
