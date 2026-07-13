"""Aegis: A Python SQL migration static analyzer."""

from aegis.engine import RuleEngine
from aegis.parser.models import ParsedMigration
from aegis.rules.registry import RuleRegistry

__version__ = "0.3.0-alpha.1"

__all__ = [
    "ParsedMigration",
    "RuleEngine",
    "RuleRegistry",
]
