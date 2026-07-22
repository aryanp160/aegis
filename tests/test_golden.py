import importlib
import json
import sys
from pathlib import Path

import pytest

from aegis.engine import RuleEngine
from aegis.parser.core import SqlParser


def test_golden_violations_match() -> None:
    workspace_dir = Path(__file__).parent.parent.resolve()
    input_file = workspace_dir / "tests" / "golden" / "input_unsafe.sql"
    golden_file = workspace_dir / "tests" / "golden" / "expected_output.json"

    # Reload rule packs to guarantee they are registered
    # even if other tests cleared the registry
    for module_name in [
        "aegis.rules.best_practices",
        "aegis.rules.high_risk",
        "aegis.rules.operational",
    ]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

    parser = SqlParser()
    parse_result = parser.parse(input_file)
    assert parse_result.success is True
    assert parse_result.migration is not None

    engine = RuleEngine()
    result = engine.analyze([parse_result.migration])

    # Serialize violations, normalizing paths to be relative to the workspace root
    serialized_violations = []
    for v in result.violations:
        rel_path = Path(v.path).relative_to(workspace_dir).as_posix()
        serialized_violations.append({
            "code": v.code,
            "message": v.message,
            "path": rel_path,
            "line": v.line,
            "column": v.column,
            "severity": v.severity.value,
            "title": v.title,
            "category": v.category.value if v.category else None,
            "risk": v.risk,
            "remediation": v.remediation,
            "documentation_url": v.documentation_url,
        })

    # If golden file doesn't exist, we can write it (useful for initializing the test)
    if not golden_file.is_file():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        with open(golden_file, "w", encoding="utf-8") as f:
            json.dump(serialized_violations, f, indent=2)
        # Fail the first time so the developer knows a new golden was created
        pytest_fail = True
    else:
        pytest_fail = False

    with open(golden_file, encoding="utf-8") as f:
        expected_violations = json.load(f)

    # Assert match
    assert serialized_violations == expected_violations, (
        f"Violations do not match golden output! "
        f"If the change is expected, update {golden_file}."
    )

    if pytest_fail:
        pytest.fail(
            f"Initialized new golden file at {golden_file}. "
            "Please review and commit."
        )
