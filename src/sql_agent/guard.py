"""Read-only SQL guard: parse, allow-list SELECT only, force a row limit."""
import sqlglot
from sqlglot import exp

MAX_ROWS = 1000
# any node of these types anywhere in the tree (CTE bodies, subqueries) is rejected
_FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
              exp.Command, exp.Merge, exp.Pragma, exp.Attach, exp.Copy)


class UnsafeSQL(ValueError):
    pass


def check_sql(sql: str, max_rows: int = MAX_ROWS) -> str:
    """Return a safe, row-limited query or raise UnsafeSQL."""
    try:
        stmts = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as e:
        raise UnsafeSQL(f"unparseable: {e}") from e
    if len(stmts) != 1 or stmts[0] is None:
        raise UnsafeSQL("exactly one statement allowed")
    tree = stmts[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise UnsafeSQL(f"only SELECT allowed, got {type(tree).__name__}")
    if tree.find(*_FORBIDDEN):
        raise UnsafeSQL("forbidden statement inside query")
    tree = tree.limit(max_rows) if not tree.args.get("limit") else tree
    return tree.sql(dialect="sqlite")
