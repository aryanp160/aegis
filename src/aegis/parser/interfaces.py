from abc import ABC, abstractmethod
from pathlib import Path

from aegis.parser.models import ParseResult


class BaseParser(ABC):
    """Base interface for all SQL migration parsers in Aegis."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """Parses a migration file into a ParseResult.

        Args:
            file_path: The Path to the migration SQL file.

        Returns:
            A ParseResult containing success state and details.
        """
        pass
