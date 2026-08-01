from sqlglot import exp

from aegis.config import AegisConfig
from aegis.parser.models import ParsedMigration
from aegis.rules.models import Violation


def check_rules(migration: ParsedMigration, config: AegisConfig) -> list[Violation]:
    """Evaluates AST nodes of a parsed migration against configuration rules.

    Args:
        migration: The parsed SQL migration details.
        config: Aegis configuration holding rule policies.

    Returns:
        A list of identified Violation instances.
    """
    violations: list[Violation] = []

    for node in migration.ast_nodes:
        # Rule 1: allow_drop_table
        if not config.rules.allow_drop_table:
            # Check if this is a DROP TABLE statement
            if isinstance(node, exp.Drop) and node.args.get("kind") == "TABLE":
                sev = config.severities.get("allow_drop_table", "error")
                violations.append(
                    Violation(
                        file_path=migration.path,
                        rule_name="allow_drop_table",
                        severity=sev,
                        message=(
                            "Table deletion detected. Dropping tables is "
                            "forbidden by current policy."
                        ),
                    )
                )

        # ALTER TABLE checks
        if isinstance(node, exp.Alter) and node.args.get("kind") == "TABLE":
            actions = node.args.get("actions", [])
            for action in actions:
                # Rule 2: allow_drop_column
                if not config.rules.allow_drop_column:
                    is_drop_col = (
                        isinstance(action, exp.Drop)
                        and action.args.get("kind") == "COLUMN"
                    )
                    if is_drop_col:
                        sev = config.severities.get("allow_drop_column", "error")
                        violations.append(
                            Violation(
                                file_path=migration.path,
                                rule_name="allow_drop_column",
                                severity=sev,
                                message=(
                                    "Column deletion detected. Dropping columns is "
                                    "forbidden by current policy."
                                ),
                            )
                        )

                # Rule 3: allow_rename_table
                if not config.rules.allow_rename_table:
                    if isinstance(action, exp.AlterRename):
                        sev = config.severities.get("allow_rename_table", "warning")
                        violations.append(
                            Violation(
                                file_path=migration.path,
                                rule_name="allow_rename_table",
                                severity=sev,
                                message=(
                                    "Table renaming detected. Renaming tables is "
                                    "forbidden by current policy."
                                ),
                            )
                        )

    return sorted(violations, key=lambda v: v.rule_name)
