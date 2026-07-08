import logging

from aegis.rules.base import Rule

logger = logging.getLogger("aegis.rules.registry")


class RuleRegistry:
    """Registry managing the catalog of active static analysis rules."""

    _rules: dict[str, type[Rule]] = {}

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
            raise ValueError(
                f"Rule class {rule_cls.__name__} lacks metadata code."
            )

        code = metadata.code
        cls._rules[code] = rule_cls
        logger.debug("Registered static analysis rule: %s", code)
        return rule_cls

    @classmethod
    def get_rules(cls) -> list[type[Rule]]:
        """Retrieves all registered rule classes.

        Returns:
            A list of registered Rule subclasses.
        """
        return list(cls._rules.values())

    @classmethod
    def unregister_all(cls) -> None:
        """Clears all registered rules from the active registry catalog."""
        cls._rules.clear()
        logger.debug("Cleared all rules from registry.")
