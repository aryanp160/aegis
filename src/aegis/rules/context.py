from typing import Any

from aegis.parser.models import ParsedMigration


class RuleContext:
    """Encapsulates context information passed to validation rules."""

    def __init__(self, migration: ParsedMigration, config: Any = None) -> None:
        """Initializes the RuleContext.

        Args:
            migration: The ParsedMigration model containing AST and statements.
            config: Optional configuration settings reference.
        """
        self.migration = migration
        self.config = config
