import logging
from pathlib import Path

from aegis.parser.errors import FileDiscoveryError

logger = logging.getLogger("aegis.parser.discovery")


def discover_migration_files(
    directory: Path, _visited: set[Path] | None = None
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
        visited: Optional, kept for backward compatibility signature.

    Returns:
        A sorted list of resolved Path objects pointing to SQL files.

    Raises:
        FileDiscoveryError: If the specified directory is invalid or inaccessible.
    """
    try:
        resolved_root = directory.resolve()
    except Exception as e:
        raise FileDiscoveryError(
            f"Failed to resolve directory path {directory}: {e}"
        ) from e

    if not resolved_root.is_dir():
        raise FileDiscoveryError(
            f"Discovery target is not a valid directory: {directory}"
        )

    visited_strs = {str(resolved_root)}
    discovered_files = _discover_migration_files_recursive(resolved_root, visited_strs)

    # Deterministic alphabetical sorting by filename
    discovered_files.sort(key=lambda p: p.name)
    return discovered_files


def _discover_migration_files_recursive(
    directory: Path, visited: set[str]
) -> list[Path]:
    discovered_files: list[Path] = []

    try:
        for path in directory.iterdir():
            # Ignore hidden files/directories and __pycache__
            if path.name.startswith(".") or path.name == "__pycache__":
                continue

            if path.is_symlink():
                try:
                    resolved_path = path.resolve()
                except Exception as e:
                    logger.warning("Skipping unresolvable symlink %s: %s", path, e)
                    continue

                path_str = str(resolved_path)
                if path_str in visited:
                    logger.warning("Skipping circular reference: %s", path)
                    continue

                visited.add(path_str)
                if resolved_path.is_dir():
                    discovered_files.extend(
                        _discover_migration_files_recursive(resolved_path, visited)
                    )
                elif resolved_path.is_file() and resolved_path.suffix.lower() == ".sql":
                    discovered_files.append(resolved_path)
            elif path.is_dir():
                path_str = str(path.absolute())
                if path_str in visited:
                    continue
                visited.add(path_str)
                discovered_files.extend(
                    _discover_migration_files_recursive(path, visited)
                )
            elif path.is_file() and path.suffix.lower() == ".sql":
                discovered_files.append(path.absolute())

    except Exception as e:
        raise FileDiscoveryError(
            f"Error occurred while scanning directory {directory}: {e}"
        ) from e

    return discovered_files
