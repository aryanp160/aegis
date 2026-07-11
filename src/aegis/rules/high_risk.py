import logging

from sqlglot import exp

from aegis.parser.enums import SQLDialect
from aegis.rules.base import ASTVisitor, Rule
from aegis.rules.context import RuleContext
from aegis.rules.enums import Category, Severity
from aegis.rules.models import RuleMetadata, Violation
from aegis.rules.registry import RuleRegistry

logger = logging.getLogger("aegis.rules.high_risk")


# --- AEG-101 ---
AEG_101_META = RuleMetadata(
    code="AEG-101",
    name="Missing CONCURRENTLY on CREATE INDEX",
    description=(
        "Index creation locks the table against concurrent writes by default "
        "in PostgreSQL."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "High risk of application downtime due to write locks on the target "
        "table during index building."
    ),
    explanation=(
        "By default, PostgreSQL builds indexes by locking the table against "
        "write operations. For large tables, this lock can cause application "
        "requests to queue up and eventually time out. Creating the index "
        "CONCURRENTLY avoids acquiring this lock, allowing writes to proceed."
    ),
    unsafe_sql="CREATE INDEX idx_users_email ON users (email);",
    safe_sql="CREATE INDEX CONCURRENTLY idx_users_email ON users (email);",
    remediation="Add the CONCURRENTLY keyword to your CREATE INDEX statement.",
    documentation_url="https://aegis.dev/rules/AEG-101",
)


@RuleRegistry.register
class MissingConcurrentlyCreateIndexRule(Rule):
    """Checks for PostgreSQL CREATE INDEX lacking the CONCURRENTLY modifier."""

    metadata = AEG_101_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        # Only relevant for PostgreSQL
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations = []
        for node in context.migration.ast_nodes:
            if isinstance(node, exp.Create) and node.args.get("kind") == "INDEX":
                if not node.args.get("concurrently"):
                    violations.append(
                        Violation(
                            code=self.metadata.code,
                            message=(
                                "CREATE INDEX statement is missing the "
                                "CONCURRENTLY modifier."
                            ),
                            path=context.migration.path,
                            line=node.meta.get("line")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            column=node.meta.get("column")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            severity=self.metadata.severity,
                        )
                    )
        return violations


# --- AEG-102 ---
AEG_102_META = RuleMetadata(
    code="AEG-102",
    name="Missing CONCURRENTLY on DROP INDEX",
    description=(
        "Index dropping locks the table against concurrent reads/writes by "
        "default in PostgreSQL."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "High risk of blocking application queries because PostgreSQL locks "
        "the table during a standard DROP INDEX."
    ),
    explanation=(
        "Dropping an index locks the table against reads and writes. "
        "On active tables, this lock can cause immediate query queuing. "
        "Using DROP INDEX CONCURRENTLY avoids locking concurrent traffic."
    ),
    unsafe_sql="DROP INDEX idx_users_email;",
    safe_sql="DROP INDEX CONCURRENTLY idx_users_email;",
    remediation="Add the CONCURRENTLY keyword to your DROP INDEX statement.",
    documentation_url="https://aegis.dev/rules/AEG-102",
)


@RuleRegistry.register
class MissingConcurrentlyDropIndexRule(Rule):
    """Checks for PostgreSQL DROP INDEX statements lacking the CONCURRENTLY modifier."""

    metadata = AEG_102_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        # Only relevant for PostgreSQL
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations = []
        for node in context.migration.ast_nodes:
            if isinstance(node, exp.Drop) and node.args.get("kind") == "INDEX":
                if not node.args.get("concurrently"):
                    violations.append(
                        Violation(
                            code=self.metadata.code,
                            message=(
                                "DROP INDEX statement is missing the "
                                "CONCURRENTLY modifier."
                            ),
                            path=context.migration.path,
                            line=node.meta.get("line")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            column=node.meta.get("column")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            severity=self.metadata.severity,
                        )
                    )
        return violations


# --- AEG-103 ---
AEG_103_META = RuleMetadata(
    code="AEG-103",
    name="Unsafe NOT NULL column addition",
    description=(
        "Adding a NOT NULL column to an existing table without a default value "
        "fails if rows exist."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "Can cause migration failures or app errors if the table contains "
        "existing rows, as new columns default to NULL."
    ),
    explanation=(
        "Adding a NOT NULL column to an existing table requires all existing rows "
        "to satisfy the NOT NULL constraint. If no default value is defined, the "
        "database will attempt to fill existing rows with NULL, violating the "
        "constraint."
    ),
    unsafe_sql="ALTER TABLE users ADD COLUMN age INT NOT NULL;",
    safe_sql="ALTER TABLE users ADD COLUMN age INT NOT NULL DEFAULT 0;",
    remediation=(
        "Provide a DEFAULT value when adding a NOT NULL column, or add the "
        "column as nullable first."
    ),
    documentation_url="https://aegis.dev/rules/AEG-103",
)


@RuleRegistry.register
class UnsafeNotNullColumnAdditionRule(Rule):
    """Checks for ALTER TABLE adding NOT NULL columns without default values."""

    metadata = AEG_103_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        violations = []

        class NotNullVisitor(ASTVisitor):
            def visit_columndef(self, node: exp.ColumnDef) -> None:
                # We only care about ColumnDef added inside an Alter statement
                parent = node.parent
                is_alter = False
                while parent:
                    if isinstance(parent, exp.Alter):
                        is_alter = True
                        break
                    parent = parent.parent

                if is_alter:
                    is_not_null = False
                    has_default = False
                    for constraint in node.find_all(exp.ColumnConstraint):
                        if isinstance(constraint.kind, exp.NotNullColumnConstraint):
                            is_not_null = True
                        elif isinstance(constraint.kind, exp.DefaultColumnConstraint):
                            has_default = True

                    if is_not_null and not has_default:
                        violations.append(
                            Violation(
                                code=AEG_103_META.code,
                                message=(
                                    "Adding a NOT NULL column without a default "
                                    "value is unsafe."
                                ),
                                path=context.migration.path,
                                line=node.meta.get("line")
                                if hasattr(node, "meta") and node.meta
                                else None,
                                column=node.meta.get("column")
                                if hasattr(node, "meta") and node.meta
                                else None,
                                severity=AEG_103_META.severity,
                            )
                        )
                self.generic_visit(node)

        visitor = NotNullVisitor()
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations


# --- AEG-104 ---
AEG_104_META = RuleMetadata(
    code="AEG-104",
    name="Table rewriting type conversions",
    description=(
        "Altering or modifying a column's data type can rewrite the table, "
        "locking it during the rewrite."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "High risk of locking the table and causing application request queues "
        "to saturate."
    ),
    explanation=(
        "Changing column data types often forces the database to rewrite the "
        "entire table on disk to update the layout. This is a heavy blocking "
        "operation that locks reads/writes depending on the database engine."
    ),
    unsafe_sql="ALTER TABLE users ALTER COLUMN age TYPE TEXT;",
    safe_sql=(
        "-- safe alternatives: add a new column, backfill data, and drop the "
        "old column"
    ),
    remediation=(
        "Use a dual-column transition strategy: add new column, backfill "
        "asynchronously, then rename/drop."
    ),
    documentation_url="https://aegis.dev/rules/AEG-104",
)


@RuleRegistry.register
class TableRewritingTypeConversionRule(Rule):
    """Checks for column modification statements that alter column data types."""

    metadata = AEG_104_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        violations = []

        class TypeConversionVisitor(ASTVisitor):
            def visit_altercolumn(self, node: exp.AlterColumn) -> None:
                if node.args.get("dtype"):
                    violations.append(
                        Violation(
                            code=AEG_104_META.code,
                            message=(
                                "Altering column data type is unsafe and "
                                "causes table rewrites."
                            ),
                            path=context.migration.path,
                            line=node.meta.get("line")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            column=node.meta.get("column")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            severity=AEG_104_META.severity,
                        )
                    )
                self.generic_visit(node)

            def visit_modifycolumn(self, node: exp.ModifyColumn) -> None:
                violations.append(
                    Violation(
                        code=AEG_104_META.code,
                        message=(
                            "Modifying column type is unsafe and causes table "
                            "rewrites."
                        ),
                        path=context.migration.path,
                        line=node.meta.get("line")
                        if hasattr(node, "meta") and node.meta
                        else None,
                        column=node.meta.get("column")
                        if hasattr(node, "meta") and node.meta
                        else None,
                        severity=AEG_104_META.severity,
                    )
                )
                self.generic_visit(node)

        visitor = TypeConversionVisitor()
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations


# --- AEG-105 ---
AEG_105_META = RuleMetadata(
    code="AEG-105",
    name="Foreign keys without NOT VALID",
    description=(
        "Adding foreign key constraints locks tables for a full validation scan "
        "unless NOT VALID is specified."
    ),
    category=Category.DESTRUCTIVE,
    severity=Severity.ERROR,
    risk=(
        "Blocks table access by acquiring strong locks for historical "
        "verification checks."
    ),
    explanation=(
        "Adding a foreign key validates all pre-existing rows in the table. "
        "For large tables, this lock can cause downtime. Adding the constraint "
        "with NOT VALID skips immediate scan validation, allowing safe "
        "validation at a later point."
    ),
    unsafe_sql=(
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) "
        "REFERENCES users (id);"
    ),
    safe_sql=(
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) "
        "REFERENCES users (id) NOT VALID;"
    ),
    remediation=(
        "Add the NOT VALID clause, then validate constraints using ALTER TABLE "
        "VALIDATE CONSTRAINT in a separate transaction."
    ),
    documentation_url="https://aegis.dev/rules/AEG-105",
)


@RuleRegistry.register
class ForeignKeyWithoutNotValidRule(Rule):
    """Checks for PostgreSQL foreign key additions missing the NOT VALID option."""

    metadata = AEG_105_META

    def evaluate(self, context: RuleContext) -> list[Violation]:
        # Only relevant for PostgreSQL
        if context.migration.dialect != SQLDialect.POSTGRESQL:
            return []

        violations = []

        class ForeignKeyVisitor(ASTVisitor):
            def visit_foreignkey(self, node: exp.ForeignKey) -> None:
                # Find the parent Alter statement
                parent = node.parent
                alter_node = None
                while parent:
                    if isinstance(parent, exp.Alter):
                        alter_node = parent
                        break
                    parent = parent.parent

                if alter_node and not alter_node.args.get("not_valid"):
                    violations.append(
                        Violation(
                            code=AEG_105_META.code,
                            message="Adding a foreign key without NOT VALID is unsafe.",
                            path=context.migration.path,
                            line=node.meta.get("line")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            column=node.meta.get("column")
                            if hasattr(node, "meta") and node.meta
                            else None,
                            severity=AEG_105_META.severity,
                        )
                    )
                self.generic_visit(node)

        visitor = ForeignKeyVisitor()
        for node in context.migration.ast_nodes:
            visitor.visit(node)

        return violations
