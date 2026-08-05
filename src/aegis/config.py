import tomllib
from pathlib import Path
from typing import Any, Self

<<<<<<< HEAD
from pydantic import BaseModel, Field, ValidationError, field_validator
=======
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aegis.rules.enums import Severity
>>>>>>> develop


class ConfigError(Exception):
    """Base exception for all configuration-related errors."""


class ConfigParseError(ConfigError):
    """Raised when the configuration file contains invalid TOML syntax."""


class ConfigValidationError(ConfigError):
    """Raised when the configuration parameters break validation rules."""


class RuleOverrideConfig(BaseModel):
    """Configuration overrides for a specific static analysis rule."""

    enabled: bool = Field(default=True, description="Enable or disable the rule.")
    severity: Severity | None = Field(
        default=None, description="Override severity for the rule."
    )


class RuleConfig(BaseModel):
    """Configuration options for static analysis migration rules."""

    model_config = ConfigDict(extra="allow")

    allow_drop_table: bool = Field(
        default=False, description="Allow dropping tables in migrations."
    )
    allow_drop_column: bool = Field(
        default=False, description="Allow dropping columns in migrations."
    )
    allow_rename_table: bool = Field(
        default=True, description="Allow renaming tables in migrations."
    )

    @model_validator(mode="after")
    def validate_overrides(self) -> Self:
        """Validates that any extra dictionary properties are valid overrides."""
        if self.model_extra:
            for key, val in self.model_extra.items():
                if isinstance(val, dict):
                    try:
                        RuleOverrideConfig(**val)
                    except ValidationError as e:
                        raise ValueError(
                            f"Invalid override settings for rule '{key}': {e}"
                        ) from e
        return self

    def get_overrides(self) -> dict[str, RuleOverrideConfig]:
        """Extracts rule-specific overrides from extra configuration fields."""
        overrides = {}
        if self.model_extra:
            for key, val in self.model_extra.items():
                if isinstance(val, dict):
                    overrides[key] = RuleOverrideConfig(**val)
        return overrides


class AegisConfig(BaseModel):
    """Main configuration schema for the Aegis analyzer."""

    dialect: str = Field(
        default="postgres",
        description="The default SQL dialect to parse (e.g. postgres, mysql, sqlite).",
    )
    rules: RuleConfig = Field(
        default_factory=RuleConfig,
        description="Active rule assertions and policies.",
    )
<<<<<<< HEAD
    severities: dict[str, str] = Field(
        default_factory=lambda: {
            "allow_drop_table": "error",
            "allow_drop_column": "error",
            "allow_rename_table": "warning",
        },
        description="Severity overrides for rules.",
    )

    @field_validator("severities", mode="before")
    @classmethod
    def merge_severities_defaults(cls, v: Any) -> Any:
        defaults = {
            "allow_drop_table": "error",
            "allow_drop_column": "error",
            "allow_rename_table": "warning",
        }
        if isinstance(v, dict):
            return {**defaults, **v}
        return v
=======
    ignore_rules: list[str] = Field(
        default_factory=list,
        description="List of rule codes to ignore globally.",
    )
    suppressions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Map of file path patterns to rule codes to suppress.",
    )
>>>>>>> develop

    @classmethod
    def from_toml(cls, toml_content: str) -> Self:
        """Parses TOML content into an AegisConfig instance.

        Raises:
            ConfigParseError: If TOML syntax is invalid.
            ConfigValidationError: If parameter values fail verification.
        """
        try:
            data = tomllib.loads(toml_content)
        except Exception as e:
            raise ConfigParseError(f"Failed to parse TOML configuration: {e}") from e

        # Extract nested configuration
        config_data = data
        if (
            "tool" in data
            and isinstance(data["tool"], dict)
            and "aegis" in data["tool"]
        ):
            config_data = data["tool"]["aegis"]
        elif "aegis" in data:
            config_data = data["aegis"]

        try:
            return cls(**config_data)
        except ValidationError as e:
            raise ConfigValidationError(
                f"Configuration parameters failed validation: {e}"
            ) from e


def discover_config(start_path: Path) -> Path | None:
    """Recursively walks up parent directories to discover Aegis configuration files.

    Looks for standalone 'aegis.toml' or a 'pyproject.toml' containing a
    '[tool.aegis]' section.

    Args:
        start_path: The directory path to start searching from.

    Returns:
        Path to the discovered configuration file, or None if not found.
    """
    current_dir = start_path.resolve()
    if start_path.is_file():
        current_dir = start_path.parent.resolve()

    for directory in [current_dir] + list(current_dir.parents):
        # Look for standalone aegis.toml
        aegis_toml = directory / "aegis.toml"
        if aegis_toml.is_file():
            return aegis_toml

        # Look for pyproject.toml containing a tool.aegis section
        pyproject_toml = directory / "pyproject.toml"
        if pyproject_toml.is_file():
            try:
                with open(pyproject_toml, "rb") as f:
                    data = tomllib.load(f)
                if (
                    "tool" in data
                    and isinstance(data["tool"], dict)
                    and "aegis" in data["tool"]
                ):
                    return pyproject_toml
            except Exception:
                # Ignore malformed files during discovery and keep searching
                continue

    return None


def load_config(
    config_path: Path | None = None, start_path: Path | None = None
) -> AegisConfig:
    """Loads configuration from a given file or discovers it from the workspace.

    If no config file is found, returns default configuration.

    Args:
        config_path: Exact path to the configuration file (skips discovery).
        start_path: Path to start discovery from (defaults to CWD).

    Raises:
        ConfigParseError: If the configuration file contains invalid TOML.
        ConfigValidationError: If configuration parameters fail validation.
    """
    target_path = config_path
    if target_path is None:
        search_start = start_path if start_path is not None else Path.cwd()
        target_path = discover_config(search_start)

    if target_path is None or not target_path.is_file():
        return AegisConfig()

    with open(target_path, encoding="utf-8") as f:
        content = f.read()

    return AegisConfig.from_toml(content)
