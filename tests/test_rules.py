from pathlib import Path

from sqlglot import exp

from aegis.config import AegisConfig
from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules.engine import check_rules


def test_check_rules_empty_ast() -> None:
    """Verifies that an empty AST returns no violations."""
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.POSTGRESQL,
        raw_content="-- Only comments",
        statements=[],
        ast_nodes=[],
    )
    config = AegisConfig()
    violations = check_rules(migration, config)
    assert not violations


def test_check_rules_allow_drop_table() -> None:
    """Verifies table drop policy behavior."""
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.POSTGRESQL,
        raw_content="DROP TABLE users;",
        statements=["DROP TABLE users;"],
        ast_nodes=[exp.Drop(this=exp.to_table("users"), kind="TABLE")],
    )

    # Policy: allow_drop_table = False (default)
    config = AegisConfig()
    config.rules.allow_drop_table = False
    violations = check_rules(migration, config)
    assert len(violations) == 1
    assert violations[0].rule_name == "allow_drop_table"
    assert "Table deletion detected" in violations[0].message

    # Policy: allow_drop_table = True
    config.rules.allow_drop_table = True
    violations = check_rules(migration, config)
    assert not violations


def test_check_rules_allow_drop_column() -> None:
    """Verifies column drop policy behavior."""
    alter_action = exp.Drop(this=exp.to_column("email"), kind="COLUMN")
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.POSTGRESQL,
        raw_content="ALTER TABLE users DROP COLUMN email;",
        statements=["ALTER TABLE users DROP COLUMN email;"],
        ast_nodes=[
            exp.Alter(
                this=exp.to_table("users"),
                kind="TABLE",
                actions=[alter_action],
            )
        ],
    )

    # Policy: allow_drop_column = False (default)
    config = AegisConfig()
    config.rules.allow_drop_column = False
    violations = check_rules(migration, config)
    assert len(violations) == 1
    assert violations[0].rule_name == "allow_drop_column"
    assert "Column deletion detected" in violations[0].message

    # Policy: allow_drop_column = True
    config.rules.allow_drop_column = True
    violations = check_rules(migration, config)
    assert not violations


def test_check_rules_allow_rename_table() -> None:
    """Verifies table rename policy behavior."""
    alter_action = exp.AlterRename(this=exp.to_table("customers"))
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.POSTGRESQL,
        raw_content="ALTER TABLE users RENAME TO customers;",
        statements=["ALTER TABLE users RENAME TO customers;"],
        ast_nodes=[
            exp.Alter(
                this=exp.to_table("users"),
                kind="TABLE",
                actions=[alter_action],
            )
        ],
    )

    # Policy: allow_rename_table = True (default)
    config = AegisConfig()
    config.rules.allow_rename_table = True
    violations = check_rules(migration, config)
    assert not violations

    # Policy: allow_rename_table = False
    config.rules.allow_rename_table = False
    violations = check_rules(migration, config)
    assert len(violations) == 1
    assert violations[0].rule_name == "allow_rename_table"
    assert "Table renaming detected" in violations[0].message
    # Default severity is warning
    assert violations[0].severity == "warning"

    # Policy: allow_rename_table = False with severity override
    config.severities["allow_rename_table"] = "error"
    violations = check_rules(migration, config)
    assert len(violations) == 1
    assert violations[0].severity == "error"
