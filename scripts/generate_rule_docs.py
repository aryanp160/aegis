import os
from pathlib import Path

# Need to import rules modules so they register themselves
import aegis.rules.best_practices
import aegis.rules.high_risk
import aegis.rules.operational
from aegis.rules.registry import RuleRegistry

DOCS_DIR = Path("docs/rules")

TEMPLATE = """# {code}: {name}

**Category:** {category}
**Severity:** {severity}
**Risk:** {risk}

## Problem

{description}

## Why it is dangerous

{explanation}

## Unsafe SQL

```sql
{unsafe_sql}
```

## Safe SQL

```sql
{safe_sql}
```

## Remediation

{remediation}

## References

- [Documentation]({documentation_url})
"""

def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    rules = RuleRegistry.get_rules(include_disabled=True)
    print(f"Discovered {len(rules)} rules.")

    for rule_cls in rules:
        meta = rule_cls.metadata
        
        content = TEMPLATE.format(
            code=meta.code,
            name=meta.name,
            category=meta.category.value.title(),
            severity=meta.severity.value.upper(),
            risk=meta.risk,
            description=meta.description,
            explanation=meta.explanation,
            unsafe_sql=meta.unsafe_sql,
            safe_sql=meta.safe_sql,
            remediation=meta.remediation,
            documentation_url=meta.documentation_url,
        )

        file_path = DOCS_DIR / f"{meta.code}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Generated {file_path}")

if __name__ == "__main__":
    main()
