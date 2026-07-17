from collections.abc import Generator
from pathlib import Path

import pytest

from aegis.config import AegisConfig, ConfigValidationError
from aegis.engine import RuleEngine
from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules.base import Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry


class MockRuleOne(Rule):
    metadata = RuleMetadata(
        code="AEG-M01",
        name="Mock Rule One",
        description="First mock rule.",
        category=Category.STYLE,
        severity=Severity.ERROR,
        risk="Low",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        return [
            Violation(
                code="AEG-M01",
                message="Mock violation 1",
                path=context.migration.path,
                line=1,
                severity=self.metadata.severity,
            )
        ]


class MockRuleTwo(Rule):
    metadata = RuleMetadata(
        code="AEG-M02",
        name="Mock Rule Two",
        description="Second mock rule.",
        category=Category.STYLE,
        severity=Severity.WARNING,
        risk="Low",
        explanation="Test",
        unsafe_sql="",
        safe_sql="",
        remediation="",
        documentation_url="",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        return [
            Violation(
                code="AEG-M02",
                message="Mock violation 2",
                path=context.migration.path,
                line=2,
                severity=self.metadata.severity,
            )
        ]


@pytest.fixture(autouse=True)
def clean_registry() -> Generator[None, None, None]:
    RuleRegistry.unregister_all()
    RuleRegistry.register(MockRuleOne)
    RuleRegistry.register(MockRuleTwo)
    yield
    RuleRegistry.unregister_all()


def test_ignore_rules_global_suppression() -> None:
    # 1. Without configuration, both rules produce violations
    engine = RuleEngine()
    migration = ParsedMigration(
        path=Path("0001_init.sql"),
        statements=[],
        ast_nodes=[],
        dialect=SQLDialect.POSTGRESQL,
        raw_content="",
    )
    result_before = engine.analyze([migration])
    assert len(result_before.violations) == 2

    # 2. Config ignoring AEG-M01
    config = AegisConfig.from_toml("""
ignore_rules = ["AEG-M01"]
""")
    result_after = engine.analyze([migration], config)
    assert len(result_after.violations) == 1
    assert result_after.violations[0].code == "AEG-M02"


def test_per_rule_enable_disable() -> None:
    # Disable AEG-M02
    config = AegisConfig.from_toml("""
[rules."AEG-M02"]
enabled = false
""")
    engine = RuleEngine()
    migration = ParsedMigration(
        path=Path("0001_init.sql"),
        statements=[],
        ast_nodes=[],
        dialect=SQLDialect.POSTGRESQL,
        raw_content="",
    )
    result = engine.analyze([migration], config)
    assert len(result.violations) == 1
    assert result.violations[0].code == "AEG-M01"


def test_per_rule_severity_override() -> None:
    # Override AEG-M02 severity to ERROR
    config = AegisConfig.from_toml("""
[rules."AEG-M02"]
severity = "error"
""")
    engine = RuleEngine()
    migration = ParsedMigration(
        path=Path("0001_init.sql"),
        statements=[],
        ast_nodes=[],
        dialect=SQLDialect.POSTGRESQL,
        raw_content="",
    )
    result = engine.analyze([migration], config)
    assert len(result.violations) == 2
    # Verify AEG-M02's violation now has Severity.ERROR
    v_m02 = [v for v in result.violations if v.code == "AEG-M02"][0]
    assert v_m02.severity == Severity.ERROR


def test_per_file_suppression() -> None:
    # Suppress AEG-M01 in file 0001_init.sql only
    config = AegisConfig.from_toml("""
[suppressions]
"0001_init.sql" = ["AEG-M01"]
""")
    engine = RuleEngine()
    migration_1 = ParsedMigration(
        path=Path("0001_init.sql"),
        statements=[],
        ast_nodes=[],
        dialect=SQLDialect.POSTGRESQL,
        raw_content="",
    )
    migration_2 = ParsedMigration(
        path=Path("0002_update.sql"),
        statements=[],
        ast_nodes=[],
        dialect=SQLDialect.POSTGRESQL,
        raw_content="",
    )
    result = engine.analyze([migration_1, migration_2], config)

    # Total violations should be:
    # migration_1: AEG-M02 (AEG-M01 suppressed)
    # migration_2: AEG-M01, AEG-M02
    assert len(result.violations) == 3

    m1_violations = [v for v in result.violations if v.path.name == "0001_init.sql"]
    assert len(m1_violations) == 1
    assert m1_violations[0].code == "AEG-M02"


def test_invalid_config_validation() -> None:
    # Invalid severity type
    with pytest.raises(ConfigValidationError):
        AegisConfig.from_toml("""
[rules."AEG-M02"]
severity = "invalid-severity-type"
""")

    # Invalid ignore_rules type
    with pytest.raises(ConfigValidationError):
        AegisConfig.from_toml("""
ignore_rules = 12345
""")

    # Invalid suppressions format
    with pytest.raises(ConfigValidationError):
        AegisConfig.from_toml("""
[suppressions]
"0001_init.sql" = "not-a-list"
""")
