from collections.abc import Generator
from pathlib import Path

import pytest
import sqlglot

from aegis.engine import RuleEngine
from aegis.parser.enums import SQLDialect
from aegis.parser.models import ParsedMigration
from aegis.rules.base import Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry


class MockDiagRule(Rule):
    metadata = RuleMetadata(
        code="AEG-DIAG",
        name="Diagnostic Rule",
        description="Fires diagnostic details on Alter Column.",
        category=Category.DESTRUCTIVE,
        severity=Severity.ERROR,
        risk="Severe rewrite of table.",
        explanation="Test explanation.",
        unsafe_sql="ALTER TABLE x ALTER COLUMN y TYPE int;",
        safe_sql="",
        remediation="Run it concurrently or validity check.",
        documentation_url="https://aegis.dev/AEG-DIAG",
    )

    def evaluate(self, context: RuleContext) -> list[Violation]:
        violations = []
        for node in context.migration.ast_nodes:
            # Look for Alter statements
            if isinstance(node, sqlglot.exp.Alter):
                violations.append(
                    Violation(
                        code=self.metadata.code,
                        message="Mock diagnostic message",
                        path=context.migration.path,
                        line=node.meta.get("line") if node.meta else 1,
                        column=node.meta.get("column") if node.meta else 0,
                        severity=self.metadata.severity,
                        node=node,
                    )
                )
        return violations


@pytest.fixture(autouse=True)
def clean_registry() -> Generator[None, None, None]:
    RuleRegistry.unregister_all()
    RuleRegistry.register(MockDiagRule)
    yield
    RuleRegistry.unregister_all()


def test_violation_diagnostic_enrichment() -> None:
    sql = "ALTER TABLE users ALTER COLUMN age TYPE INT;"
    migration = ParsedMigration(
        path=Path("0001_diag.sql"),
        statements=[sql],
        ast_nodes=[sqlglot.parse_one(sql, read="postgres")],
        dialect=SQLDialect.POSTGRESQL,
        raw_content=sql,
    )

    engine = RuleEngine()
    result = engine.analyze([migration])
    assert len(result.violations) == 1

    v = result.violations[0]
    # Check enriched metadata
    assert v.title == "Diagnostic Rule"
    assert v.category == Category.DESTRUCTIVE
    assert v.risk == "Severe rewrite of table."
    assert v.remediation == "Run it concurrently or validity check."
    assert v.documentation_url == "https://aegis.dev/AEG-DIAG"

    # Check SQL Snippet (exact compiled SQL statement)
    assert v.sql_snippet is not None
    assert "ALTER TABLE" in v.sql_snippet

    # Check Highlighted SQL (contains caret pointing to start position)
    assert v.highlighted_sql is not None
    assert "ALTER TABLE" in v.highlighted_sql
    assert "^" in v.highlighted_sql


def test_violation_rendering() -> None:
    v = Violation(
        code="AEG-MOCK",
        message="A mock violation",
        path=Path("0001_init.sql"),
        line=1,
        column=5,
        severity=Severity.ERROR,
        title="Mock Title",
        category=Category.STYLE,
        sql_snippet="SELECT * FROM users;",
        highlighted_sql="   1 | SELECT * FROM users;\n     |      ^",
        risk="Data loss.",
        remediation="Fix it.",
        documentation_url="https://example.com/mock",
    )

    rendered = v.render()
    assert "[ERROR] AEG-MOCK: Mock Title" in rendered
    assert "Category:  Style" in rendered
    assert "File:      0001_init.sql:1:5" in rendered
    assert "Risk:      Data loss." in rendered
    assert "Fix:       Fix it." in rendered
    assert "Docs:      https://example.com/mock" in rendered
    assert "Highlighted SQL:" in rendered
    assert rendered == str(v)
