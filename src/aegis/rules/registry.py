import logging
from typing import Any

from aegis.rules.base import Rule
from aegis.rules.enums import Category, Severity

logger = logging.getLogger("aegis.rules.registry")


class RuleRegistry:
    """Registry managing the catalog of active static analysis rules."""

    _rules: dict[str, type[Rule]] = {}
    _disabled_rules: set[str] = set()

    @classmethod
    def register(cls, rule_cls: type[Rule]) -> type[Rule]:
        """Registers a rule class using its metadata code identifier.

        Can be used as a class decorator.

        Args:
            rule_cls: The Rule subclass type to register.

        Returns:
            The registered rule class type.

        Raises:
            ValueError: If the rule class lacks metadata or a code identifier.
        """
        # Validate that the rule class has a metadata attribute with a valid code
        metadata = getattr(rule_cls, "metadata", None)
        if not metadata or not getattr(metadata, "code", None):
            raise ValueError(f"Rule class {rule_cls.__name__} lacks metadata code.")

        code = metadata.code
        cls._rules[code] = rule_cls
        logger.debug("Registered static analysis rule: %s", code)
        return rule_cls

    @classmethod
    def get_rule(cls, code: str) -> type[Rule] | None:
        """Retrieves a specific rule class by its metadata code identifier.

        Args:
            code: The rule code (e.g., 'AEG-101').

        Returns:
            The rule class if found, otherwise None.
        """
        return cls._rules.get(code)

    @classmethod
    def enable_rule(cls, code: str) -> None:
        """Enables a previously disabled rule.

        Args:
            code: The rule code to enable.
        """
        if code in cls._disabled_rules:
            cls._disabled_rules.remove(code)
            logger.debug("Enabled rule: %s", code)

    @classmethod
    def disable_rule(cls, code: str) -> None:
        """Disables a rule so it is not returned in discovery unless requested.

        Args:
            code: The rule code to disable.
        """
        if code in cls._rules:
            cls._disabled_rules.add(code)
            logger.debug("Disabled rule: %s", code)

    @classmethod
    def get_rules(
        cls,
        categories: list[Category] | None = None,
        severities: list[Severity] | None = None,
        include_disabled: bool = False,
    ) -> list[type[Rule]]:
        """Retrieves registered rule classes based on filters.

        Args:
            categories: Optional list of categories to filter by.
            severities: Optional list of severities to filter by.
            include_disabled: If True, includes explicitly disabled rules.

        Returns:
            A list of registered Rule subclasses matching the criteria.
        """
        filtered_rules = []
        for code, rule_cls in cls._rules.items():
            if not include_disabled and code in cls._disabled_rules:
                continue

            metadata = rule_cls.metadata
            if categories and metadata.category not in categories:
                continue

            if severities and metadata.severity not in severities:
                continue

            filtered_rules.append(rule_cls)

        return filtered_rules

    @classmethod
    def get_statistics(cls) -> dict[str, Any]:
        """Returns statistics about the currently registered rules.

        Returns:
            A dictionary containing counts and distributions.
        """
        stats: dict[str, Any] = {
            "total_rules": len(cls._rules),
            "enabled_rules": len(cls._rules) - len(cls._disabled_rules),
            "disabled_rules": len(cls._disabled_rules),
            "by_category": {},
            "by_severity": {},
        }

        for rule_cls in cls._rules.values():
            meta = rule_cls.metadata
            cat = meta.category.name
            sev = meta.severity.name
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1

        return stats

    @classmethod
    def apply_config(cls, config: Any) -> None:
        """Applies configuration settings to configure rule enable/disable states.

        Args:
            config: An AegisConfig instance to apply to the registry.
        """
        # Reset disabled rules first
        cls._disabled_rules.clear()

        # Apply global ignore list
        if hasattr(config, "ignore_rules"):
            for code in config.ignore_rules:
                cls.disable_rule(code)

        # Apply individual rule overrides
        if hasattr(config, "rules") and hasattr(config.rules, "get_overrides"):
            overrides = config.rules.get_overrides()
            for code, override in overrides.items():
                if not override.enabled:
                    cls.disable_rule(code)
                else:
                    cls.enable_rule(code)

    @classmethod
    def load_plugins(cls, paths: list[str]) -> None:
        """Stubs the entrypoint for loading external plugin rules dynamically.

        Args:
            paths: A list of directory paths to scan for plugins.

        Raises:
            NotImplementedError: As plugins are not yet supported.
        """
        raise NotImplementedError("Plugin loading is not implemented yet.")

    @classmethod
    def unregister_all(cls) -> None:
        """Clears all registered rules and disabled states from the registry."""
        cls._rules.clear()
        cls._disabled_rules.clear()
        logger.debug("Cleared all rules from registry.")
