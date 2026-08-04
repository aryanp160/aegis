"""Aegis: A Python SQL migration static analyzer."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("aegis")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.4.0-beta.1"
