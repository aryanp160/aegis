from pathlib import Path


def discover_sql_files(directory_path: Path) -> list[Path]:
    """Recursively finds all SQL files in the directory.

    Files are returned sorted alphabetically by name to preserve migration order.

    Args:
        directory_path: The directory path to search.

    Returns:
        List of Path objects pointing to SQL files.
    """
    if not directory_path.is_dir():
        return []

    sql_files = list(directory_path.rglob("*.sql"))
    # Sort files to ensure deterministic migration execution order
    sql_files.sort(key=lambda p: p.name)
    return sql_files


def discover_migration_directories(root_path: Path) -> list[Path]:
    """Finds all subdirectories under root_path that contain at least one .sql file.

    Args:
        root_path: The root directory to start scanning from.

    Returns:
        Sorted list of directories containing migration files.
    """
    if not root_path.is_dir():
        return []

    discovered_dirs: set[Path] = set()
    for sql_file in root_path.rglob("*.sql"):
        discovered_dirs.add(sql_file.parent.resolve())

    return sorted(discovered_dirs)
