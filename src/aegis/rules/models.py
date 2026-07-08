from pathlib import Path

from pydantic import BaseModel, Field

from aegis.rules.enums import Category, Severity


class RuleMetadata(BaseModel):
    """Pydantic model representing rule specifications and characteristics."""

    code: str = Field(description="Unique code identifying the rule (e.g., AEG-101).")
    name: str = Field(description="Short human-readable name of the rule.")
    description: str = Field(description="Extended documentation of the rule's checks.")
    category: Category = Field(description="The category category of the rule.")
    severity: Severity = Field(description="Default severity rating for rule breaches.")


class Violation(BaseModel):
    """Pydantic model mapping a specific rule violation in a SQL script."""

    code: str = Field(description="Identifies the violated rule.")
    message: str = Field(
        description="Descriptive diagnostic details explaining the breach."
    )
    path: Path = Field(
        description="Path to the migration SQL file containing the violation."
    )
    line: int | None = Field(
        default=None, description="Line number of the violating instruction."
    )
    column: int | None = Field(
        default=None, description="Column offset of the violation."
    )
    severity: Severity = Field(
        description="Severity rating of this specific violation."
    )


class AnalysisResult(BaseModel):
    """Pydantic model encapsulating the summary results of static migration analysis."""

    violations: list[Violation] = Field(
        default_factory=list,
        description="List of all detected violations across migrations.",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Elapsed analysis duration in milliseconds.",
    )

    @property
    def total_errors(self) -> int:
        """Returns total error count."""
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def total_warnings(self) -> int:
        """Returns total warning count."""
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @property
    def total_infos(self) -> int:
        """Returns total info count."""
        return sum(1 for v in self.violations if v.severity == Severity.INFO)
