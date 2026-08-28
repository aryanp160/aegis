"""Aegis: A Python SQL migration static analyzer."""

import importlib.metadata
from typing import Any

try:
    __version__ = importlib.metadata.version("aegis")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.4.0-beta.2"

# Lazy imports for public APIs to avoid overhead on CLI startup
_lazy_imports = {
    "RuleEngine": "aegis.engine",
    "ParsedMigration": "aegis.parser.models",
    "RuleRegistry": "aegis.rules.registry",
}


def __getattr__(name: str) -> Any:
    if name in _lazy_imports:
        import importlib

        module = importlib.import_module(_lazy_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ParsedMigration",
    "RuleEngine",
    "RuleRegistry",
]
