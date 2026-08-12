"""Aegis: A Python SQL migration static analyzer."""

import importlib.metadata

from aegis.engine import RuleEngine
from aegis.parser.models import ParsedMigration
from aegis.rules.registry import RuleRegistry

try:
    __version__ = importlib.metadata.version("aegis")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.4.0-beta.2"

__all__ = [
    "ParsedMigration",
    "RuleEngine",
    "RuleRegistry",
]
