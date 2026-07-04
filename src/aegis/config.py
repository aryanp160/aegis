import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class RuleConfig(BaseModel):
    """Configuration options for static analysis migration rules."""

    allow_drop_table: bool = Field(
        default=False, description="Allow dropping tables in migrations."
    )
    allow_drop_column: bool = Field(
        default=False, description="Allow dropping columns in migrations."
    )
    allow_rename_table: bool = Field(
        default=True, description="Allow renaming tables in migrations."
    )


class AegisConfig(BaseModel):
    """Main Aegis configuration schema."""

    dialect: str = Field(
        default="postgres",
        description="The default SQL dialect to parse (e.g. postgres, mysql, sqlite).",
    )
    rules: RuleConfig = Field(
        default_factory=RuleConfig,
        description="Active rule assertions and policies.",
    )


def load_config(config_path: Path | None = None) -> AegisConfig:
    """Loads and validates configuration from a TOML file.

    If file doesn't exist or is not specified, returns default configuration.
    """
    if config_path is None or not config_path.is_file():
        return AegisConfig()

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Allow nesting config under [tool.aegis] or [aegis] or at the root
        aegis_data = data
        if "tool" in data and "aegis" in data["tool"]:
            aegis_data = data["tool"]["aegis"]
        elif "aegis" in data:
            aegis_data = data["aegis"]

        return AegisConfig(**aegis_data)
    except Exception:
        # Returns default config in case of validation or parsing failures
        return AegisConfig()
