import pytest

from sql_agent.guard import UnsafeSQL, check_sql

BAD = [
    "DROP TABLE users", "DELETE FROM t", "UPDATE t SET a=1", "INSERT INTO t VALUES (1)",
    "SELECT 1; DROP TABLE t", "PRAGMA writable_schema=1", "ATTACH 'x.db' AS x",
    "WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d", "", "not sql at all ((",
]


@pytest.mark.parametrize("sql", BAD)
def test_blocked(sql):
    with pytest.raises(UnsafeSQL):
        check_sql(sql)


def test_allowed_and_limited():
    assert check_sql("SELECT * FROM t").endswith("LIMIT 1000")
    assert check_sql("SELECT * FROM t LIMIT 5").endswith("LIMIT 5")
    check_sql("WITH c AS (SELECT 1) SELECT * FROM c")
