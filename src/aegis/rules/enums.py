from enum import StrEnum


class Severity(StrEnum):
    """Linter severity levels for rule violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(StrEnum):
    """Categorization of linter rules."""

    DESTRUCTIVE = "destructive"
    COMPATIBILITY = "compatibility"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
