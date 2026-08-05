from pathlib import Path

import sqlglot

from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules import RuleContext, Severity
from aegis.rules.best_practices import (
    SerialUsageRule,
    TimestampWithoutTimeZoneRule,
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


# --- AEG-108 Tests ---
def test_aeg_108_postgres_serial_datatype() -> None:
    sql = "CREATE TABLE users (id SERIAL PRIMARY KEY);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = SerialUsageRule(SerialUsageRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-108"
    assert violations[0].severity == Severity.WARNING


def test_aeg_108_postgres_bigserial_datatype() -> None:
    sql = "ALTER TABLE users ADD COLUMN id BIGSERIAL;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = SerialUsageRule(SerialUsageRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-108"


def test_aeg_108_postgres_identity_safe() -> None:
    sql = "CREATE TABLE users (id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = SerialUsageRule(SerialUsageRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_108_mysql_ignored() -> None:
    sql = "CREATE TABLE users (id SERIAL PRIMARY KEY);"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = SerialUsageRule(SerialUsageRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


# --- AEG-110 Tests ---
def test_aeg_110_postgres_timestamp_without_tz() -> None:
    sql = "CREATE TABLE users (created_at TIMESTAMP);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = TimestampWithoutTimeZoneRule(TimestampWithoutTimeZoneRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-110"
    assert violations[0].severity == Severity.WARNING


def test_aeg_110_postgres_timestamp_with_tz_explicit() -> None:
    sql = "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE;"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = TimestampWithoutTimeZoneRule(TimestampWithoutTimeZoneRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 1
    assert violations[0].code == "AEG-110"


def test_aeg_110_postgres_timestamptz_safe() -> None:
    sql = "CREATE TABLE users (created_at TIMESTAMPTZ);"
    ctx = _make_context(sql, SQLDialect.POSTGRESQL)
    rule = TimestampWithoutTimeZoneRule(TimestampWithoutTimeZoneRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0


def test_aeg_110_mysql_ignored() -> None:
    sql = "CREATE TABLE users (created_at TIMESTAMP);"
    ctx = _make_context(sql, SQLDialect.MYSQL)
    rule = TimestampWithoutTimeZoneRule(TimestampWithoutTimeZoneRule.metadata)
    violations = rule.evaluate(ctx)

    assert len(violations) == 0
