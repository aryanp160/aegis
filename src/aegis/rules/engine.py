import logging
import time
from typing import Any

from aegis.parser.models import ParsedMigration
from aegis.rules.context import RuleContext
from aegis.rules.models import AnalysisResult, Violation
from aegis.rules.registry import RuleRegistry

logger = logging.getLogger("aegis.rules.engine")


class RuleEngine:
    """Orchestrates linting analysis by evaluating rules on SQL migrations."""

    def __init__(self) -> None:
        """Initializes the RuleEngine."""
        pass

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
        for migration in migrations:
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

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Static analysis finished in %.2f ms.", duration_ms)

        return AnalysisResult(violations=violations, duration_ms=duration_ms)
