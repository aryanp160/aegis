from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParsedMigration(BaseModel):
    """Pydantic model representing a fully parsed SQL migration file."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path = Field(
        description="The absolute or relative file path to the migration SQL file."
    )
    dialect: str = Field(
        description="The SQL dialect identified for this migration (e.g. postgres)."
    )
    raw_content: str = Field(
        description="The complete raw string content of the migration file."
    )
    statements: list[str] = Field(
        default_factory=list,
        description="Splitted raw string statement statements.",
    )
    ast_nodes: list[Any] = Field(
        default_factory=list,
        description="List of parsed sqlglot AST expression nodes.",
    )
