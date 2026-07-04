import sqlglot
from sqlglot import exp


def test_sqlglot_parsing_works() -> None:
    """Verifies that sqlglot parsed SQL statement compiles and identifies AST nodes."""
    sql = "ALTER TABLE users ADD COLUMN age INT;"
    expression = sqlglot.parse_one(sql)

    assert isinstance(expression, exp.Alter)
    assert expression.this.name == "users"

    actions = expression.args.get("actions")
    assert actions is not None
    assert len(actions) == 1
    assert isinstance(actions[0], exp.ColumnDef)
    assert actions[0].this.name == "age"
