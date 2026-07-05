import logging
from pathlib import Path

from aegis.parser.errors import FileDiscoveryError

logger = logging.getLogger("aegis.parser.discovery")


def discover_migration_files(
    directory: Path, visited: set[Path] | None = None
) -> list[Path]:
    """Recursively scans a directory for SQL migration files.

    Rules:
    - Filters out files that do not have a '.sql' extension.
    - Ignores hidden files/directories (starting with '.').
    - Ignores '__pycache__' directories.
    - Sorts files alphabetically by name to ensure stable ordering.
    - Protects against circular loops via symlink validation.

    Args:
        directory: The directory path to search.
        visited: Internal set to track resolved directory paths to prevent loops.

    Returns:
        A sorted list of resolved Path objects pointing to SQL files.

    Raises:
        FileDiscoveryError: If the specified directory is invalid or inaccessible.
    """
    if visited is None:
        visited = set()

    try:
        resolved_dir = directory.resolve()
    except Exception as e:
        raise FileDiscoveryError(
            f"Failed to resolve directory path {directory}: {e}"
        ) from e

    if not resolved_dir.is_dir():
        raise FileDiscoveryError(
            f"Discovery target is not a valid directory: {directory}"
        )

    # Symlink safety check to prevent circular loops
    if resolved_dir in visited:
        logger.warning("Skipping circular directory reference: %s", directory)
        return []

    visited.add(resolved_dir)
    discovered_files: list[Path] = []

    try:
        for path in resolved_dir.iterdir():
            # Ignore hidden files/directories and __pycache__
            if path.name.startswith(".") or path.name == "__pycache__":
                continue

            if path.is_dir():
                # Recurse subdirectories
                discovered_files.extend(discover_migration_files(path, visited))
            elif path.is_file() and path.suffix.lower() == ".sql":
                discovered_files.append(path.resolve())
    except Exception as e:
        raise FileDiscoveryError(
            f"Error occurred while scanning directory {resolved_dir}: {e}"
        ) from e

    # Deterministic alphabetical sorting by filename
    discovered_files.sort(key=lambda p: p.name)
    return discovered_files
