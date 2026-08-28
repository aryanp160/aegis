import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configures global application logging using an optimized handler."""
    # Ensure external libraries like sqlglot don't pollute CLI
    # logs with debugging details
    logging.getLogger("sqlglot").setLevel(logging.WARNING)

    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    if level == "DEBUG":
        from rich.logging import RichHandler

        handler = RichHandler(rich_tracebacks=True, show_path=False)
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logging.basicConfig(
        level=level,
        handlers=[handler],
    )
