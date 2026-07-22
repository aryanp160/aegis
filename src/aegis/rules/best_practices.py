import logging
from pathlib import Path

from sqlglot import exp

from aegis.parser.enums import SQLDialect
from aegis.rules.base import ASTVisitor, Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry

logger = logging.getLogger("aegis.rules.best_practices")


# --- AEG-108 ---
AEG_108_META = RuleMetadata(
    code="AEG-108",
    name="SERIAL usage",
    description=(
        "Using SERIAL/BIGSERIAL/SMALLSERIAL data types is discouraged in modern "
        "PostgreSQL."
    ),
    category=Category.STYLE,
    severity=Severity.WARNING,
    risk=(
        "Older SERIAL types create non-standard sequence objects that can cause "
        "sequence ownership bugs during migrations."
    ),
    explanation=(
        "PostgreSQL 10+ supports standard IDENTITY columns (GENERATED ALWAYS AS "
        "IDENTITY). Identity columns conform to the SQL standard and manage "
        "sequences cleanly."
    ),
    unsafe_sql="CREATE TABLE users (id SERIAL PRIMARY KEY);",
    safe_sql="CREATE TABLE users (id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY);",
    remediation=(
        "Replace SERIAL with INT GENERATED ALWAYS AS IDENTITY, or BIGSERIAL "
        "with BIGINT GENERATED ALWAYS AS IDENTITY."
    ),
    documentation_url="https://aegis.dev/rules/AEG-108",
)


class SerialVisitor(ASTVisitor):
    def __init__(
        self,
        violations: list[Violation],
        path: Path,
        code: str,
        severity: Severity,
    ) -> None:
        super().__init__()
        self.violations = violations
        self.path = path
        self.code = code
        self.severity = severity

    def visit_datatype(self, node: exp.DataType) -> None:
        if node.this in (
            exp.DataType.Type.SERIAL,
            exp.DataType.Type.BIGSERIAL,
            exp.DataType.Type.SMALLSERIAL,
        ):
            self.violations.append(
                Violation(
                    code=self.code,
                    message=f"Discouraged data type '{node.this}' detected.",
                    path=self.path,
                    line=(
                        node.meta.get("line")
                        if hasattr(node, "meta") and node.meta
                        else None
                    ),
                    column=(
                        node.meta.get("column")
                        if hasattr(node, "meta") and node.meta
                        else None
                    ),
                    severity=self.severity,
                    node=node,
                )
            )
        self.generic_visit(node)


@RuleRegistry.register
class SerialUsageRule(Rule):
    """Checks for PostgreSQL SERIAL type columns."""

    metadata = AEG_108_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations: list[Violation] = []
        visitor = SerialVisitor(
            violations=violations,
            path=context.migration.path,
            code=self.metadata.code,
            severity=self.metadata.severity,
        )
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations


# --- AEG-110 ---
AEG_110_META = RuleMetadata(
    code="AEG-110",
    name="TIMESTAMP WITHOUT TIME ZONE",
    description="Using TIMESTAMP WITHOUT TIME ZONE is discouraged in PostgreSQL.",
    category=Category.STYLE,
    severity=Severity.WARNING,
    risk=(
        "Can cause subtle timezone bugs when querying or comparing records from "
        "systems running in different timezones."
    ),
    explanation=(
        "TIMESTAMP WITHOUT TIME ZONE discards timezone details. PostgreSQL "
        "converts values to local timezone dynamically on TIMESTAMPTZ, keeping "
        "dates timezone-safe."
    ),
    unsafe_sql="CREATE TABLE users (created_at TIMESTAMP);",
    safe_sql="CREATE TABLE users (created_at TIMESTAMPTZ);",
    remediation=(
        "Replace TIMESTAMP or TIMESTAMP WITHOUT TIME ZONE with TIMESTAMPTZ or "
        "TIMESTAMP WITH TIME ZONE."
    ),
    documentation_url="https://aegis.dev/rules/AEG-110",
)


class TimestampVisitor(ASTVisitor):
    def __init__(
        self,
        violations: list[Violation],
        path: Path,
        code: str,
        severity: Severity,
    ) -> None:
        super().__init__()
        self.violations = violations
        self.path = path
        self.code = code
        self.severity = severity

    def visit_datatype(self, node: exp.DataType) -> None:
        if node.this == exp.DataType.Type.TIMESTAMP:
            self.violations.append(
                Violation(
                    code=self.code,
                    message=(
                        "TIMESTAMP without timezone is discouraged. Use "
                        "TIMESTAMPTZ."
                    ),
                    path=self.path,
                    line=(
                        node.meta.get("line")
                        if hasattr(node, "meta") and node.meta
                        else None
                    ),
                    column=(
                        node.meta.get("column")
                        if hasattr(node, "meta") and node.meta
                        else None
                    ),
                    severity=self.severity,
                    node=node,
                )
            )
        self.generic_visit(node)


@RuleRegistry.register
class TimestampWithoutTimeZoneRule(Rule):
    """Checks for PostgreSQL TIMESTAMP (without timezone) column data types."""

    metadata = AEG_110_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations: list[Violation] = []
        visitor = TimestampVisitor(
            violations=violations,
            path=context.migration.path,
            code=self.metadata.code,
            severity=self.metadata.severity,
        )
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations
