from sqlglot import exp

from aegis.config import AegisConfig
from aegis.parser.models import ParsedMigration
from aegis.rules.enums import Severity
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
                violations.append(
                    Violation(
                        code="AEG-107",
                        message=(
                            "Table deletion detected. Dropping tables is "
                            "forbidden by current policy."
                        ),
                        path=migration.path,
                        severity=Severity.ERROR,
                        node=node,
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
                        violations.append(
                            Violation(
                                code="AEG-107",
                                message=(
                                    "Column deletion detected. Dropping columns is "
                                    "forbidden by current policy."
                                ),
                                path=migration.path,
                                severity=Severity.ERROR,
                                node=action,
                            )
                        )

                # Rule 3: allow_rename_table
                if not config.rules.allow_rename_table:
                    if isinstance(action, exp.AlterRename):
                        violations.append(
                            Violation(
                                code="AEG-108",
                                message=(
                                    "Table renaming detected. Renaming tables is "
                                    "forbidden by current policy."
                                ),
                                path=migration.path,
                                severity=Severity.WARNING,
                                node=action,
                            )
                        )

    return sorted(violations, key=lambda v: v.code)
