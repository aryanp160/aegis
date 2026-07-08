from abc import ABC, abstractmethod

from sqlglot.expressions import Expression

from aegis.rules.context import RuleContext
from aegis.rules.models import RuleMetadata, Violation


class ASTVisitor:
    """Base visitor walking and routing sqlglot AST nodes to subclass handlers."""

    def visit(self, node: Expression) -> None:
        """Visits a node by routing to its type-specific method (e.g. visit_create).

        Args:
            node: The sqlglot Expression node to visit.
        """
        method_name = f"visit_{node.__class__.__name__.lower()}"
        visitor_method = getattr(self, method_name, self.generic_visit)
        visitor_method(node)

    def generic_visit(self, node: Expression) -> None:
        """Default fallback method that walks down all child expressions.

        Args:
            node: The parent sqlglot Expression node.
        """
        for child in node.iter_expressions():
            self.visit(child)


class Rule(ABC):
    """Abstract Base Class for all Aegis migration static analysis checks."""

    metadata: RuleMetadata

    def __init__(self, metadata: RuleMetadata) -> None:
        """Initializes the Rule with metadata.

        Args:
            metadata: Characteristics describing the rule (e.g. code, severity).
        """
        self.metadata = metadata

    @abstractmethod
    def evaluate(self, context: RuleContext) -> list[Violation]:
        """Analyzes a parsed migration and collects any rule breaches.

        Args:
            context: Context containing target migration AST and config details.

        Returns:
            A list of detected Violation objects.
        """
        pass
