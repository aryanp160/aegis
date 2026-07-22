from pathlib import Path

import sqlglot

from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules import RuleContext, Severity
from aegis.rules.operational import (
    ConcurrentlyInsideTransactionRule,
    DropTableColumnProtectionRule,
    MissingLockTimeoutRule,
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


# --- AEG-106 Tests ---
def test_aeg_106_postgres_concurrently_inside_transaction() -> None:
    sql = "BEGIN; CREATE INDEX CONCURRENTLY idx ON users (email); COMMIT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = ConcurrentlyInsideTransactionRule(ConcurrentlyInsideTransactionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-106"
    assert violations[0].severity == Severity.ERROR


def test_aeg_106_postgres_concurrently_outside_transaction() -> None:
    sql = "CREATE INDEX CONCURRENTLY idx ON users (email);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = ConcurrentlyInsideTransactionRule(ConcurrentlyInsideTransactionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_106_mysql_ignored() -> None:
    sql = "BEGIN; CREATE INDEX CONCURRENTLY idx ON users (email); COMMIT;"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = ConcurrentlyInsideTransactionRule(ConcurrentlyInsideTransactionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-107 Tests ---
def test_aeg_107_drop_table_without_override() -> None:
    sql = "DROP TABLE users;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = DropTableColumnProtectionRule(DropTableColumnProtectionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-107"
    assert violations[0].severity == Severity.ERROR


def test_aeg_107_drop_column_without_override() -> None:
    sql = "ALTER TABLE users DROP COLUMN email;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = DropTableColumnProtectionRule(DropTableColumnProtectionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-107"


def test_aeg_107_drop_table_with_line_override() -> None:
    sql = "-- aegis:allow-destructive\nDROP TABLE users;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = DropTableColumnProtectionRule(DropTableColumnProtectionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_107_drop_column_with_block_override() -> None:
    sql = "/* aegis:allow-destructive */\nALTER TABLE users DROP COLUMN email;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = DropTableColumnProtectionRule(DropTableColumnProtectionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-109 Tests ---
def test_aeg_109_postgres_missing_lock_timeout() -> None:
    sql = "ALTER TABLE users ADD COLUMN age INT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingLockTimeoutRule(MissingLockTimeoutRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-109"
    assert violations[0].severity == Severity.WARNING


def test_aeg_109_postgres_with_lock_timeout_eq() -> None:
    sql = "SET lock_timeout = 2000; ALTER TABLE users ADD COLUMN age INT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingLockTimeoutRule(MissingLockTimeoutRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_109_postgres_with_lock_timeout_to() -> None:
    sql = "SET lock_timeout TO '2s'; ALTER TABLE users ADD COLUMN age INT;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = MissingLockTimeoutRule(MissingLockTimeoutRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_109_mysql_ignored() -> None:
    sql = "ALTER TABLE users ADD COLUMN age INT;"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = MissingLockTimeoutRule(MissingLockTimeoutRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_106_postgres_concurrently_inside_rollback_transaction() -> None:
    sql = "BEGIN; CREATE INDEX CONCURRENTLY idx ON users (email); ROLLBACK;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = ConcurrentlyInsideTransactionRule(ConcurrentlyInsideTransactionRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-106"
    assert violations[0].severity == Severity.ERROR
