import json

from sql_agent import tools
from sql_agent.db import seed
from sql_agent.tools import call_tool


def setup_module():
    seed()


def test_destructive_returns_error_and_db_intact():
    out, err = call_tool("run_sql", {"sql": "DROP TABLE orders"})
    assert err
    out, err = call_tool("run_sql", {"sql": "SELECT COUNT(*) FROM orders"})
    assert not err and json.loads(out)["rows"] == [[2000]]


def test_bad_input_and_unknown_tool():
    assert call_tool("run_sql", {})[1]
    assert call_tool("nope", {})[1]
    assert call_tool("export_csv", {"sql": "SELECT 1", "filename": "../x.csv"})[1]


def test_malformed_tool_output_recovers(monkeypatch):
    monkeypatch.setitem(tools.TOOLS, "run_sql", (tools.SQLArgs, lambda a: object(), ""))
    assert call_tool("run_sql", {"sql": "SELECT 1"})[1]  # unserialisable -> error, no crash


def test_forced_failure_recovers(monkeypatch):
    def boom(a):
        raise TimeoutError("forced")
    monkeypatch.setitem(tools.TOOLS, "run_sql", (tools.SQLArgs, boom, ""))
    out, err = call_tool("run_sql", {"sql": "SELECT 1"})
    assert err and "forced" in out
