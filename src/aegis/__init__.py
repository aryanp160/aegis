"""Aegis: A Python SQL migration static analyzer."""

<<<<<<< HEAD
import importlib.metadata

try:
    __version__ = importlib.metadata.version("aegis")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.4.0-beta.1"
=======
from aegis.engine import RuleEngine
from aegis.parser.models import ParsedMigration
from aegis.rules.registry import RuleRegistry

__version__ = "0.3.0-alpha.1"

__all__ = [
    "ParsedMigration",
    "RuleEngine",
    "RuleRegistry",
]
>>>>>>> develop
