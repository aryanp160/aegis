from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
import sqlglot
from sqlglot import exp
from sqlglot.expressions import Expression

from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules import (
    AnalysisResult,
    ASTVisitor,
    Category,
    Rule,
    RuleContext,
    RuleMetadata,
    RuleRegistry,
    Severity,
    Violation,
)
from aegis.engine import RuleEngine


class MockVisitor(ASTVisitor):
    """Mock ASTVisitor subclass verifying visitor routing patterns."""

    def __init__(self) -> None:
        self.visited_creates = 0
        self.visited_alters = 0

    def visit_create(self, node: exp.Create) -> None:
        self.visited_creates += 1
        self.generic_visit(node)

    def visit_alter(self, node: exp.Alter) -> None:
        self.visited_alters += 1
        self.generic_visit(node)


# Define metadata for a mock rule
MOCK_METADATA = RuleMetadata(
    code="AEG-MOCK",
    name="Mock Rule",
    description="Fires a warning on any alter statements.",
    category=Category.STYLE,
    severity=Severity.WARNING,
    risk="Low risk.",
    explanation="Test mock explanation.",
    unsafe_sql="ALTER TABLE x DROP y;",
    safe_sql="-- safe sql mock",
    remediation="Do not run alter.",
    documentation_url="https://aegis.dev/mock",
)


@RuleRegistry.register
class MockAlterRule(Rule):
    """Mock rule generating a violation on any Alter nodes."""

    metadata = MOCK_METADATA

    def evaluate(self, context: RuleContext) -> list[Violation]:
        violations = []
        for node in context.migration.ast_nodes:
            if isinstance(node, exp.Alter):
                violations.append(
                    Violation(
                        code=self.metadata.code,
                        message="Mock alter violation detected.",
                        path=context.migration.path,
                        line=1,
                        column=1,
                        severity=self.metadata.severity,
                    )
                )
        return violations


@pytest.fixture(autouse=True)
def cleanup_registry() -> Generator[None, None, None]:
    """Pre-test fixture ensuring registry starts clean and is restored."""
    # Store original rules
    original_rules = list(RuleRegistry._rules.items())
    RuleRegistry.unregister_all()
    # Register our test rule for active runs
    RuleRegistry.register(MockAlterRule)
    yield
    # Restore original rules
    RuleRegistry._rules.clear()
    for code, rule_cls in original_rules:
        RuleRegistry._rules[code] = rule_cls


def test_severity_and_category_values() -> None:
    """Verifies defined Severity and Category enum values."""
    assert Severity.ERROR.value == "error"
    assert Severity.WARNING.value == "warning"
    assert Severity.INFO.value == "info"

    assert Category.DESTRUCTIVE.value == "destructive"
    assert Category.STYLE.value == "style"


def test_rule_registry_invalid_registration() -> None:
    """Verifies that invalid rule classes trigger ValueError on registration."""

    # Missing metadata
    class BadRuleNoMeta(Rule):
        def evaluate(self, _context: RuleContext) -> list[Violation]:
            return []

    with pytest.raises(ValueError, match="lacks metadata code"):
        RuleRegistry.register(BadRuleNoMeta)


def test_ast_visitor_routing() -> None:
    """Verifies that the ASTVisitor correctly traverses nodes and routes callbacks."""
    sql = "CREATE TABLE users (id INT); ALTER TABLE users ADD COLUMN age INT;"
    nodes = [node for node in sqlglot.parse(sql, read="postgres") if node is not None]

    visitor = MockVisitor()
    for node in nodes:
        visitor.visit(cast(Expression, node))

    assert visitor.visited_creates == 1
    assert visitor.visited_alters == 1


def test_rule_engine_analysis() -> None:
    """Verifies that the RuleEngine analyzes ParsedMigrations and aggregates results."""
    # Mock ParsedMigration containing Alter statement
    migration = ParsedMigration(
        path=Path("migration.sql"),
        dialect=SQLDialect.POSTGRESQL,
        raw_content="ALTER TABLE users ADD COLUMN age INT;",
        statements=["ALTER TABLE users ADD COLUMN age INT;"],
        ast_nodes=[
            sqlglot.parse_one("ALTER TABLE users ADD COLUMN age INT;", read="postgres")
        ],
    )

    engine = RuleEngine()
    result = engine.analyze([migration])

    assert isinstance(result, AnalysisResult)
    assert result.duration_ms >= 0.0
    assert len(result.violations) == 1
    assert result.violations[0].code == "AEG-MOCK"
    assert result.violations[0].severity == Severity.WARNING
    assert result.total_warnings == 1
    assert result.total_errors == 0
    assert result.total_infos == 0
