from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aegis.rules.enums import Category, Severity


class RuleMetadata(BaseModel):
    """Pydantic model representing rule specifications and characteristics."""

    code: str = Field(description="Unique code identifying the rule (e.g., AEG-101).")
    name: str = Field(description="Short human-readable name of the rule.")
    description: str = Field(description="Extended documentation of the rule's checks.")
    category: Category = Field(description="The category category of the rule.")
    severity: Severity = Field(description="Default severity rating for rule breaches.")
    risk: str = Field(
        description="The architectural risk or consequence of violating the rule."
    )
    explanation: str = Field(
        description="Deep dive explanation of why this check is active."
    )
    unsafe_sql: str = Field(
        description="Code example demonstrating an unsafe migration command."
    )
    safe_sql: str = Field(
        description="Code example demonstrating the safe/preferred migration command."
    )
    remediation: str = Field(
        description="Remediation steps for resolving the violation."
    )
    documentation_url: str = Field(
        description="URL to extended reference documentation."
    )


class Violation(BaseModel):
    """Pydantic model mapping a specific rule violation in a SQL script."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

    # Rich Diagnostics
    title: str | None = Field(
        default=None, description="Short human-readable rule name."
    )
    category: Category | None = Field(default=None, description="Rule category.")
    sql_snippet: str | None = Field(
        default=None, description="Violating SQL statement."
    )
    highlighted_sql: str | None = Field(
        default=None, description="Visually pointed SQL segment."
    )
    risk: str | None = Field(default=None, description="Detailed explanation of risk.")
    remediation: str | None = Field(
        default=None, description="Remediation instructions."
    )
    documentation_url: str | None = Field(
        default=None, description="Link to reference page."
    )

    # Excluded AST node reference for post-processing
    node: Any = Field(default=None, exclude=True)

    def render(self) -> str:
        """Renders a detailed diagnostic block for this violation."""
        lines = [
            f"[{self.severity.value.upper()}] {self.code}: {self.title or ''}",
            f"Category:  {self.category.value.title() if self.category else ''}",
            f"File:      {self.path}:{self.line or ''}:{self.column or ''}",
            f"Risk:      {self.risk or ''}",
            f"Fix:       {self.remediation or ''}",
            f"Docs:      {self.documentation_url or ''}",
        ]
        if self.highlighted_sql:
            lines.append("\nHighlighted SQL:")
            lines.append(self.highlighted_sql)
        elif self.sql_snippet:
            lines.append(f"\nSQL Snippet:\n    {self.sql_snippet}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()


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
