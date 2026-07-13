from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.engine import RuleEngine
from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules.base import Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry


class MockRuleError(Rule):
    metadata = RuleMetadata(
        code="MOCK-001",
        name="Error Rule",
        description="Generates an error violation.",
        category=Category.STYLE,
        severity=Severity.ERROR,
        risk="High",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        return [
            Violation(
                code="MOCK-001",
                message="Error 1",
                path=context.migration.path,
                line=10,
                column=5,
                severity=Severity.ERROR,
            )
        ]


class MockRuleWarning(Rule):
    metadata = RuleMetadata(
        code="MOCK-002",
        name="Warning Rule",
        description="Generates a warning violation.",
        category=Category.STYLE,
        severity=Severity.WARNING,
        risk="Med",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        return [
            Violation(
                code="MOCK-002",
                message="Warning 1",
                path=context.migration.path,
                line=5,
                column=0,
                severity=Severity.WARNING,
            )
        ]


class MockRuleException(Rule):
    metadata = RuleMetadata(
        code="MOCK-003",
        name="Exception Rule",
        description="Throws an exception.",
        category=Category.STYLE,
        severity=Severity.INFO,
        risk="Low",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        del context
        raise ValueError("Rule execution failed!")


class MockRuleInitException(Rule):
    metadata = RuleMetadata(
        code="MOCK-004",
        name="Init Exception Rule",
        description="Throws exception on init.",
        category=Category.STYLE,
        severity=Severity.INFO,
        risk="Low",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def __init__(self, metadata: RuleMetadata) -> None:
        del metadata
        raise ValueError("Rule init failed!")

    def evaluate(self, context: RuleContext) -> list[Violation]:
        del context
        return []


@pytest.fixture(autouse=True)
def clean_registry() -> Generator[None, None, None]:
    RuleRegistry.unregister_all()
    yield
    RuleRegistry.unregister_all()


def test_analyze_sorting_and_aggregation() -> None:
    RuleRegistry.register(MockRuleWarning)
    RuleRegistry.register(MockRuleError)

    engine = RuleEngine()
    migrations = [
        ParsedMigration(
            path=Path("b_migration.sql"),
            statements=[],
            ast_nodes=[],
            dialect=SQLDialect.POSTGRESQL,
            raw_content="",
        ),
        ParsedMigration(
            path=Path("a_migration.sql"),
            statements=[],
            ast_nodes=[],
            dialect=SQLDialect.POSTGRESQL,
            raw_content="",
        ),
    ]

    result = engine.analyze(migrations)

    # We should have 4 violations: (2 files * 2 rules)
    assert len(result.violations) == 4

    # Deterministic sorting checks:
    # 1. Severity: ERROR (weight 3) > WARNING (weight 2)
    assert result.violations[0].severity == Severity.ERROR
    assert result.violations[1].severity == Severity.ERROR
    assert result.violations[2].severity == Severity.WARNING
    assert result.violations[3].severity == Severity.WARNING

    # 2. Path: a_migration.sql < b_migration.sql
    assert result.violations[0].path == Path("a_migration.sql")
    assert result.violations[1].path == Path("b_migration.sql")
    assert result.violations[2].path == Path("a_migration.sql")
    assert result.violations[3].path == Path("b_migration.sql")

    # Check aggregation stats
    assert result.total_errors == 2
    assert result.total_warnings == 2
    assert result.total_infos == 0


def test_analyze_with_exceptions() -> None:
    # Register rules that fail at different stages
    RuleRegistry.register(MockRuleInitException)
    RuleRegistry.register(MockRuleException)
    RuleRegistry.register(MockRuleError)

    engine = RuleEngine()
    migrations = [
        ParsedMigration(
            path=Path("migration.sql"),
            statements=[],
            ast_nodes=[],
            dialect=SQLDialect.POSTGRESQL,
            raw_content="",
        ),
    ]

    result = engine.analyze(migrations)

    # Only MockRuleError should successfully yield a violation
    assert len(result.violations) == 1
    assert result.violations[0].code == "MOCK-001"
