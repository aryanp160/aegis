from pathlib import Path

from pydantic import BaseModel, Field


class Violation(BaseModel):
    """Pydantic model representing a rule violation in a migration file."""

    file_path: Path = Field(description="The path to the SQL migration file.")
    rule_name: str = Field(description="The name of the rule that was violated.")
    message: str = Field(description="Detailed violation description.")
