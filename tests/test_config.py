from pathlib import Path

import pytest

from aegis.config import (
    ConfigParseError,
    ConfigValidationError,
    discover_config,
    load_config,
)


def test_default_config_when_none_provided() -> None:
    """Verifies load_config returns default settings when path is None.

    No file is discovered in this case.
    """
    # Pass a temporary empty directory as start_path to guarantee no config
    config = load_config(start_path=Path("/"))
    assert config.dialect == "postgres"
    assert config.rules.allow_drop_table is False
    assert config.rules.allow_drop_column is False
    assert config.rules.allow_rename_table is True


def test_load_valid_toml_config_root(tmp_path: Path) -> None:
    """Verifies config loading when values are defined at the root of the TOML file."""
    config_file = tmp_path / "aegis.toml"
    config_file.write_text(
        """
dialect = "sqlite"
[rules]
allow_drop_table = true
allow_rename_table = false
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.dialect == "sqlite"
    assert config.rules.allow_drop_table is True
    assert config.rules.allow_rename_table is False


def test_load_valid_toml_config_nested(tmp_path: Path) -> None:
    """Verifies config loading when values are nested in pyproject.toml."""
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text(
        """
[tool.aegis]
dialect = "mysql"
[tool.aegis.rules]
allow_drop_column = true
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.dialect == "mysql"
    assert config.rules.allow_drop_column is True
    assert config.rules.allow_drop_table is False


def test_discover_config_standalone(tmp_path: Path) -> None:
    """Verifies discovery prioritizes standalone aegis.toml."""
    aegis_toml = tmp_path / "aegis.toml"
    aegis_toml.touch()

    discovered = discover_config(tmp_path)
    assert discovered == aegis_toml


def test_discover_config_pyproject(tmp_path: Path) -> None:
    """Verifies discovery identifies pyproject.toml if it contains tool.aegis."""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text('[tool.aegis]\ndialect = "sqlite"\n', encoding="utf-8")

    discovered = discover_config(tmp_path)
    assert discovered == pyproject_toml


def test_discover_config_pyproject_ignored_if_no_tool_aegis(tmp_path: Path) -> None:
    """Verifies discovery ignores pyproject.toml if tool.aegis is absent."""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text('[tool.poetry]\nname = "test"\n', encoding="utf-8")

    discovered = discover_config(tmp_path)
    assert discovered is None


def test_discover_config_parent_walk(tmp_path: Path) -> None:
    """Verifies discovery walks up parent directories to locate the config."""
    aegis_toml = tmp_path / "aegis.toml"
    aegis_toml.touch()

    child_dir = tmp_path / "sub" / "child"
    child_dir.mkdir(parents=True)

    discovered = discover_config(child_dir)
    assert discovered == aegis_toml


def test_load_invalid_toml_raises_parse_error(tmp_path: Path) -> None:
    """Verifies that invalid TOML syntax raises ConfigParseError."""
    config_file = tmp_path / "aegis.toml"
    config_file.write_text("invalid syntax = {[[", encoding="utf-8")

    with pytest.raises(ConfigParseError) as exc_info:
        load_config(config_file)
    assert "Failed to parse TOML configuration" in str(exc_info.value)


def test_load_invalid_types_raises_validation_error(tmp_path: Path) -> None:
    """Verifies that incorrect parameter types raise ConfigValidationError."""
    config_file = tmp_path / "aegis.toml"
    config_file.write_text(
        """
dialect = 12345
[rules]
allow_drop_table = "not-a-boolean"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_config(config_file)
    assert "Configuration parameters failed validation" in str(exc_info.value)


def test_load_config_with_severity_overrides(tmp_path: Path) -> None:
    """Verifies loading config with custom rule severities."""
    config_file = tmp_path / "aegis.toml"
    config_file.write_text(
        """
[rules."AEG-107"]
severity = "warning"
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    overrides = config.rules.get_overrides()
    assert overrides["AEG-107"].severity.value == "warning"
