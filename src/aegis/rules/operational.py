import logging

from sqlglot import exp

from aegis.parser.enums import SQLDialect
from aegis.rules.base import ASTVisitor, Rule
from aegis.rules.comments import CommentPreprocessor
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry

logger = logging.getLogger("aegis.rules.operational")


# --- AEG-106 ---
AEG_106_META = RuleMetadata(
    code="AEG-106",
    name="CONCURRENTLY inside transaction",
    description=(
        "Running index operations CONCURRENTLY inside a transaction block will "
        "fail in PostgreSQL."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "PostgreSQL throws an error and aborts the migration if a CONCURRENTLY "
        "index command runs within a transaction block."
    ),
    explanation=(
        "PostgreSQL requires CONCURRENTLY operations to run outside of "
        "transaction blocks (BEGIN/COMMIT) because they manage their own "
        "internal transactions."
    ),
    unsafe_sql="BEGIN; CREATE INDEX CONCURRENTLY idx ON users (email); COMMIT;",
    safe_sql="CREATE INDEX CONCURRENTLY idx ON users (email);",
    remediation=(
        "Remove BEGIN/COMMIT transaction statements from the migration file, or "
        "run CONCURRENTLY operations separately."
    ),
    documentation_url="https://aegis.dev/rules/AEG-106",
)


@RuleRegistry.register
class ConcurrentlyInsideTransactionRule(Rule):
    """Checks for CONCURRENTLY index operations within PostgreSQL transactions."""

    metadata = AEG_106_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations = []
        has_concurrent_op = False
        has_transaction_stmt = False
        target_node: exp.Expression | None = None

        for node in context.migration.ast_nodes:
            # Check for transaction statements (BEGIN, START TRANSACTION, COMMIT)
            if isinstance(node, (exp.Transaction, exp.Commit)):
                has_transaction_stmt = True

            # Check for concurrently create/drop index
            if isinstance(node, exp.Create) and node.args.get("kind") == "INDEX":
                if node.args.get("concurrently"):
                    has_concurrent_op = True
                    target_node = node
            elif isinstance(node, exp.Drop) and node.args.get("kind") == "INDEX":
                if node.args.get("concurrently"):
                    has_concurrent_op = True
                    target_node = node

        if has_concurrent_op and has_transaction_stmt and target_node:
            violations.append(
                Violation(
                    code=self.metadata.code,
                    message=(
                        "CONCURRENTLY index operations cannot run inside a "
                        "transaction block."
                    ),
                    path=context.migration.path,
                    line=(
                        target_node.meta.get("line")
                        if hasattr(target_node, "meta") and target_node.meta
                        else None
                    ),
                    column=(
                        target_node.meta.get("column")
                        if hasattr(target_node, "meta") and target_node.meta
                        else None
                    ),
                    severity=self.metadata.severity,
                    node=target_node,
                )
            )

        return violations


# --- AEG-107 ---
AEG_107_META = RuleMetadata(
    code="AEG-107",
    name="DROP TABLE / DROP COLUMN protection",
    description="Protects against destructive drops of tables or columns.",
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk="High risk of losing production data or causing runtime errors.",
    explanation=(
        "Dropping tables or columns deletes schema structures. The operation "
        "is disallowed unless overridden with the '-- aegis:allow-destructive' "
        "directive."
    ),
    unsafe_sql="DROP TABLE users;",
    safe_sql="-- aegis:allow-destructive\nDROP TABLE users;",
    remediation=(
        "To run, verify safety, back up data, and add the override directive "
        "'-- aegis:allow-destructive' comment."
    ),
    documentation_url="https://aegis.dev/rules/AEG-107",
)


@RuleRegistry.register
class DropTableColumnProtectionRule(Rule):
    """Checks for DROP TABLE or DROP COLUMN operations."""

    metadata = AEG_107_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        # Check override directive
        if CommentPreprocessor.has_directive(
            context.migration.raw_content, "aegis:allow-destructive"
        ):
            return []

        violations = []

        class DropVisitor(ASTVisitor):
            def visit_drop(self, node: exp.Drop) -> None:
                kind = node.args.get("kind")
                if kind in ("TABLE", "COLUMN"):
                    violations.append(
                        Violation(
                            code=AEG_107_META.code,
                            message=f"Destructive DROP {kind} statement detected.",
                            path=context.migration.path,
                            line=(
                                node.meta.get("line")
                                if hasattr(node, "meta") and node.meta
                                else None
                            ),
                            column=(
                                node.meta.get("column")
                                if hasattr(node, "meta") and node.meta
                                else None
                            ),
                            severity=AEG_107_META.severity,
                            node=node,
                        )
                    )
                self.generic_visit(node)

        visitor = DropVisitor()
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations


# --- AEG-109 ---
AEG_109_META = RuleMetadata(
    code="AEG-109",
    name="Missing SET lock_timeout",
    description="Checks that migrations specify a short lock_timeout in PostgreSQL.",
    category=Category.PERFORMANCE,
    severity=Severity.WARNING,
    risk=(
        "Without a lock_timeout, a migration waiting for a lock can block "
        "all subsequent transactions, causing an outage."
    ),
    explanation=(
        "PostgreSQL transactions block queries queued behind them. Setting a "
        "lock_timeout limits this queue time, aborting the migration if it "
        "takes too long to acquire a lock."
    ),
    unsafe_sql="ALTER TABLE users ADD COLUMN age INT;",
    safe_sql="SET lock_timeout = '2s'; ALTER TABLE users ADD COLUMN age INT;",
    remediation=(
        "Prepend a 'SET lock_timeout = ...' statement at the start of your "
        "migration script."
    ),
    documentation_url="https://aegis.dev/rules/AEG-109",
)


@RuleRegistry.register
class MissingLockTimeoutRule(Rule):
    """Checks that PostgreSQL migrations prepend a SET lock_timeout statement."""

    metadata = AEG_109_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        # If migration file contains no schema changes or statements, ignore it
        if not context.migration.ast_nodes:
            return []

        # Scan for SET lock_timeout
        has_lock_timeout = False
        for node in context.migration.ast_nodes:
            for identifier in node.find_all(exp.Identifier):
                if identifier.this.lower() == "lock_timeout":
                    # Verify parent or ancestors is a Set statement
                    parent = identifier.parent
                    while parent:
                        if isinstance(parent, exp.Set):
                            has_lock_timeout = True
                            break
                        parent = parent.parent

        if not has_lock_timeout:
            return [
                Violation(
                    code=self.metadata.code,
                    message=(
                        "Missing 'SET lock_timeout' statement in PostgreSQL migration."
                    ),
                    path=context.migration.path,
                    line=None,
                    column=None,
                    severity=self.metadata.severity,
                )
            ]

        return []
