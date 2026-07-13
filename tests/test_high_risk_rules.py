from pathlib import Path

import sqlglot

from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules import RuleContext, Severity
from aegis.rules.high_risk import (
    ForeignKeyWithoutNotValidRule,
    MissingConcurrentlyCreateIndexRule,
    MissingConcurrentlyDropIndexRule,
    TableRewritingTypeConversionRule,
    UnsafeNotNullColumnAdditionRule,
)


def _make_context(sql: str, dialect: SQLDialect) -> RuleContext:
    """Helper to compile a SQL query and build a RuleContext."""
    read_dialect = "postgres" if dialect == SQLDialect.POSTGRESQL else "mysql"
    parsed_nodes = [
        node for node in sqlglot.parse(sql, read=read_dialect) if node is not None
    ]
    migration = ParsedMigration(
        path=Path("test_migration.sql"),
        dialect=dialect,
        raw_content=sql,
        statements=[sql],
        ast_nodes=parsed_nodes,
    )
    return RuleContext(migration=migration)


# --- AEG-101 Tests ---
def test_aeg_101_postgres_missing_concurrently() -> None:
    sql = "CREATE INDEX idx_users_email ON users (email);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingConcurrentlyCreateIndexRule(
        MissingConcurrentlyCreateIndexRule.metadata
    )
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-101"
    assert violations[0].severity == Severity.ERROR


def test_aeg_101_postgres_with_concurrently() -> None:
    sql = "CREATE INDEX CONCURRENTLY idx_users_email ON users (email);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingConcurrentlyCreateIndexRule(
        MissingConcurrentlyCreateIndexRule.metadata
    )
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_101_mysql_ignored() -> None:
    sql = "CREATE INDEX idx_users_email ON users (email);"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = MissingConcurrentlyCreateIndexRule(
        MissingConcurrentlyCreateIndexRule.metadata
    )
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-102 Tests ---
def test_aeg_102_postgres_missing_concurrently() -> None:
    sql = "DROP INDEX idx_users_email;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingConcurrentlyDropIndexRule(MissingConcurrentlyDropIndexRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-102"
    assert violations[0].severity == Severity.ERROR


def test_aeg_102_postgres_with_concurrently() -> None:
    sql = "DROP INDEX CONCURRENTLY idx_users_email;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingConcurrentlyDropIndexRule(MissingConcurrentlyDropIndexRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_102_mysql_ignored() -> None:
    sql = "DROP INDEX idx_users_email;"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = MissingConcurrentlyDropIndexRule(MissingConcurrentlyDropIndexRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-103 Tests ---
def test_aeg_103_unsafe_not_null_addition() -> None:
    sql = "ALTER TABLE users ADD COLUMN age INT NOT NULL;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = UnsafeNotNullColumnAdditionRule(UnsafeNotNullColumnAdditionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-103"
    assert violations[0].severity == Severity.ERROR


def test_aeg_103_safe_not_null_with_default() -> None:
    sql = "ALTER TABLE users ADD COLUMN age INT NOT NULL DEFAULT 0;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = UnsafeNotNullColumnAdditionRule(UnsafeNotNullColumnAdditionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_103_safe_nullable_addition() -> None:
    sql = "ALTER TABLE users ADD COLUMN age INT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = UnsafeNotNullColumnAdditionRule(UnsafeNotNullColumnAdditionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_103_create_table_ignored() -> None:
    sql = "CREATE TABLE users (age INT NOT NULL);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = UnsafeNotNullColumnAdditionRule(UnsafeNotNullColumnAdditionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-104 Tests ---
def test_aeg_104_postgres_type_conversion() -> None:
    sql = "ALTER TABLE users ALTER COLUMN age TYPE TEXT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = TableRewritingTypeConversionRule(TableRewritingTypeConversionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-104"
    assert violations[0].severity == Severity.ERROR


def test_aeg_104_mysql_modify_column() -> None:
    sql = "ALTER TABLE users MODIFY COLUMN age TEXT;"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = TableRewritingTypeConversionRule(TableRewritingTypeConversionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-104"


def test_aeg_104_alter_column_default_ignored() -> None:
    sql = "ALTER TABLE users ALTER COLUMN age SET DEFAULT 42;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = TableRewritingTypeConversionRule(TableRewritingTypeConversionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-105 Tests ---
def test_aeg_105_postgres_foreign_key_missing_not_valid() -> None:
    sql = (
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_user "
        "FOREIGN KEY (user_id) REFERENCES users (id);"
    )
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = ForeignKeyWithoutNotValidRule(ForeignKeyWithoutNotValidRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-105"
    assert violations[0].severity == Severity.ERROR


def test_aeg_105_postgres_foreign_key_with_not_valid() -> None:
    sql = (
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_user "
        "FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;"
    )
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = ForeignKeyWithoutNotValidRule(ForeignKeyWithoutNotValidRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_105_mysql_ignored() -> None:
    sql = (
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_user "
        "FOREIGN KEY (user_id) REFERENCES users (id);"
    )
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = ForeignKeyWithoutNotValidRule(ForeignKeyWithoutNotValidRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0
