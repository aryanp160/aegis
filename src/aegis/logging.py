import logging
from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> None:
    """Configures global application logging using Rich handler."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    # Ensure external libraries like sqlglot don't pollute CLI logs with debugging details
    logging.getLogger("sqlglot").setLevel(logging.WARNING)
