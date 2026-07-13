import logging
import time
from typing import Any

from aegis.parser.models import ParsedMigration
from aegis.rules.base import Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Severity
from aegis.rules.models import AnalysisResult, Violation
from aegis.rules.registry import RuleRegistry

logger = logging.getLogger("aegis.rules.engine")


class RuleEngine:
    """Orchestrates linting analysis by evaluating rules on SQL migrations."""

    _SEVERITY_WEIGHT = {
        Severity.ERROR: 3,
        Severity.WARNING: 2,
        Severity.INFO: 1,
    }

    def __init__(self) -> None:
        """Initializes the RuleEngine."""
        pass

    def _analyze_migration(
        self,
        migration: ParsedMigration,
        rule_instances: list[Rule],
        config: Any = None,
    ) -> list[Violation]:
        """Runs registered rules against a single migration.

        Args:
            migration: The parsed migration to evaluate.
            rule_instances: Instantiated rules to execute.
            config: Optional configurations.

        Returns:
            A list of Violations found in this migration.
        """
        violations: list[Violation] = []
        logger.debug("Analyzing migration path: %s", migration.path)
        context = RuleContext(migration=migration, config=config)

        for rule in rule_instances:
            try:
                rule_violations = rule.evaluate(context)
                violations.extend(rule_violations)
            except Exception as e:
                logger.error(
                    "Error executing rule %s on file %s: %s",
                    rule.metadata.code,
                    migration.path,
                    e,
                )

        return violations

    def analyze(
        self, migrations: list[ParsedMigration], config: Any = None
    ) -> AnalysisResult:
        """Runs all registered lint rules over a collection of migrations.

        Args:
            migrations: List of parsed migrations containing SQL AST structures.
            config: Optional configurations to evaluate rules under.

        Returns:
            An AnalysisResult object collecting all violations and timings.
        """
        start_time = time.perf_counter()
        violations: list[Violation] = []

        rules = RuleRegistry.get_rules()
        logger.info("Executing rule engine analysis with %d active rules.", len(rules))

        # Instantiate all registered rules
        rule_instances = []
        for rule_cls in rules:
            try:
                rule_instances.append(rule_cls(rule_cls.metadata))
            except Exception as e:
                logger.error("Failed to instantiate rule %s: %s", rule_cls.__name__, e)

        # Run each migration against each rule instance
        # Designed to be easily wrapped in a ProcessPoolExecutor in the future
        for migration in migrations:
            migration_violations = self._analyze_migration(
                migration, rule_instances, config
            )
            violations.extend(migration_violations)

        # Sort violations deterministically
        violations.sort(
            key=lambda v: (
                -self._SEVERITY_WEIGHT.get(v.severity, 0),
                v.path.as_posix(),
                v.line or 0,
                v.column or 0,
                v.code,
            )
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Static analysis finished in %.2f ms.", duration_ms)

        return AnalysisResult(violations=violations, duration_ms=duration_ms)
