from collections.abc import Generator

import pytest

from aegis.rules.base import Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry


class MockRuleA(Rule):
    metadata = RuleMetadata(
        code="MOCK-001",
        name="Mock Rule A",
        description="A mock rule for testing.",
        category=Category.SECURITY,
        severity=Severity.ERROR,
        risk="High risk.",
        explanation="Test explanation.",
        unsafe_sql="SELECT *",
        safe_sql="SELECT id",
        remediation="Fix it.",
        documentation_url="http://test.com",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        del context
        return []


class MockRuleB(Rule):
    metadata = RuleMetadata(
        code="MOCK-002",
        name="Mock Rule B",
        description="Another mock rule for testing.",
        category=Category.STYLE,
        severity=Severity.WARNING,
        risk="Low risk.",
        explanation="Test explanation.",
        unsafe_sql="SELECT *",
        safe_sql="SELECT id",
        remediation="Fix it.",
        documentation_url="http://test.com",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        del context
        return []


@pytest.fixture(autouse=True)
def clean_registry() -> Generator[None, None, None]:
    """Ensure the registry is empty before and after each test."""
    RuleRegistry.unregister_all()
    yield
    RuleRegistry.unregister_all()


def test_registry_registration() -> None:
    RuleRegistry.register(MockRuleA)
    RuleRegistry.register(MockRuleB)

    rules = RuleRegistry.get_rules()
    assert len(rules) == 2
    assert MockRuleA in rules
    assert MockRuleB in rules


def test_get_rule_by_code() -> None:
    RuleRegistry.register(MockRuleA)
    assert RuleRegistry.get_rule("MOCK-001") == MockRuleA
    assert RuleRegistry.get_rule("NON-EXISTENT") is None


def test_rule_filtering_by_category() -> None:
    RuleRegistry.register(MockRuleA)
    RuleRegistry.register(MockRuleB)

    security_rules = RuleRegistry.get_rules(categories=[Category.SECURITY])
    assert len(security_rules) == 1
    assert security_rules[0] == MockRuleA

    style_rules = RuleRegistry.get_rules(categories=[Category.STYLE])
    assert len(style_rules) == 1
    assert style_rules[0] == MockRuleB


def test_rule_filtering_by_severity() -> None:
    RuleRegistry.register(MockRuleA)
    RuleRegistry.register(MockRuleB)

    error_rules = RuleRegistry.get_rules(severities=[Severity.ERROR])
    assert len(error_rules) == 1
    assert error_rules[0] == MockRuleA


def test_enable_disable_rules() -> None:
    RuleRegistry.register(MockRuleA)
    RuleRegistry.register(MockRuleB)

    # Disable MockRuleA
    RuleRegistry.disable_rule("MOCK-001")

    # It should not be returned by default get_rules()
    rules = RuleRegistry.get_rules()
    assert len(rules) == 1
    assert rules[0] == MockRuleB

    # But it should be returned if include_disabled=True
    all_rules = RuleRegistry.get_rules(include_disabled=True)
    assert len(all_rules) == 2

    # Enable MockRuleA again
    RuleRegistry.enable_rule("MOCK-001")
    rules = RuleRegistry.get_rules()
    assert len(rules) == 2


def test_get_statistics() -> None:
    RuleRegistry.register(MockRuleA)
    RuleRegistry.register(MockRuleB)
    RuleRegistry.disable_rule("MOCK-001")

    stats = RuleRegistry.get_statistics()
    assert stats["total_rules"] == 2
    assert stats["enabled_rules"] == 1
    assert stats["disabled_rules"] == 1
    assert stats["by_category"]["SECURITY"] == 1
    assert stats["by_category"]["STYLE"] == 1
    assert stats["by_severity"]["ERROR"] == 1
    assert stats["by_severity"]["WARNING"] == 1


def test_load_plugins_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        RuleRegistry.load_plugins(["some_path"])
