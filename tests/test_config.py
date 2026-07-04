from pathlib import Path

from aegis.config import load_config


def test_default_config_when_none_provided() -> None:
    """Verifies load_config returns default settings when path is None."""
    config = load_config(None)
    assert config.dialect == "postgres"
    assert config.rules.allow_drop_table is False
    assert config.rules.allow_drop_column is False
    assert config.rules.allow_rename_table is True


def test_default_config_when_file_not_found(tmp_path: Path) -> None:
    """Verifies load_config returns defaults when file does not exist."""
    config = load_config(tmp_path / "non_existent_file.toml")
    assert config.dialect == "postgres"
    assert config.rules.allow_drop_table is False


def test_load_valid_toml_config_root(tmp_path: Path) -> None:
    """Verifies config loading when values are defined at the root of the TOML file."""
    config_file = tmp_path / "config.toml"
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
    """Verifies config loading when values are defined inside the [tool.aegis] table."""
    config_file = tmp_path / "config.toml"
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


def test_load_invalid_toml_config_fallback(tmp_path: Path) -> None:
    """Verifies load_config defaults when the TOML file structure is invalid."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
invalid TOML format [[[]
""",
        encoding="utf-8",
    )
    config = load_config(config_file)
    assert config.dialect == "postgres"
