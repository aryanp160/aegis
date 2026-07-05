from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aegis.parser.enums import SQLDialect


class ParsedMigration(BaseModel):
    """Pydantic model representing a parsed migration file and its AST."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path = Field(description="Path to the migration SQL file.")
    dialect: SQLDialect = Field(
        description="The SQL dialect identified for this migration."
    )
    raw_content: str = Field(
        description="The raw string content of the migration file."
    )
    statements: list[str] = Field(
        default_factory=list,
        description="Parsed SQL statements as clean strings.",
    )
    ast_nodes: list[Any] = Field(
        default_factory=list,
        description="The parsed AST nodes from sqlglot.",
    )


class ParseResult(BaseModel):
    """Pydantic model representing the result of a parse operation."""

    success: bool = Field(description="Indicates whether the parsing was successful.")
    migration: ParsedMigration | None = Field(
        default=None,
        description="The parsed migration schema on success, or None on failure.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages encountered during parsing.",
    )
