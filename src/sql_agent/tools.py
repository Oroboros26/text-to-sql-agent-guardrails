"""Agent tools. Every tool: Pydantic-validated input, guarded read-only SQL, timeout."""
import csv
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .db import connect_ro
from .guard import check_sql

OUT = Path("out")
TIMEOUT_S = 5.0


class NoArgs(BaseModel):
    pass


class SQLArgs(BaseModel):
    sql: str = Field(max_length=2000)


class PlotArgs(SQLArgs):
    x: str
    y: str
    title: str = Field("", max_length=100)
    filename: str = Field(pattern=r"^[\w-]{1,50}\.png$")  # no path separators


class ExportArgs(SQLArgs):
    filename: str = Field(pattern=r"^[\w-]{1,50}\.csv$")


class Rows(BaseModel):  # output schema check
    columns: list[str]
    rows: list[list[Any]]


def _query(sql: str) -> Rows:
    sql = check_sql(sql)
    for attempt in range(3):
        con = connect_ro()
        deadline = time.monotonic() + TIMEOUT_S
        con.set_progress_handler(lambda d=deadline: time.monotonic() > d, 10_000)
        try:
            cur = con.execute(sql)
            return Rows(columns=[d[0] for d in cur.description],
                        rows=[list(r) for r in cur.fetchall()])
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or attempt == 2:
                raise
            time.sleep(0.2 * 2**attempt)  # backoff, only for transient lock errors
        finally:
            con.close()


def describe_schema(_: NoArgs) -> dict:
    con = connect_ro()
    try:
        return {"tables": [r[1] for r in con.execute(
            "SELECT type, sql FROM sqlite_master WHERE type='table'")]}
    finally:
        con.close()


def run_sql(a: SQLArgs) -> Rows:
    return _query(a.sql)


def plot(a: PlotArgs) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = _query(a.sql)
    xi, yi = r.columns.index(a.x), r.columns.index(a.y)
    OUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots()
    ax.bar([str(row[xi]) for row in r.rows], [row[yi] for row in r.rows])
    ax.set_title(a.title)
    fig.savefig(OUT / a.filename)
    plt.close(fig)
    return {"path": str(OUT / a.filename)}


def export_csv(a: ExportArgs) -> dict:
    r = _query(a.sql)
    OUT.mkdir(exist_ok=True)
    with open(OUT / a.filename, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(r.columns)
        w.writerows(r.rows)
    return {"path": str(OUT / a.filename), "rows": len(r.rows)}


TOOLS = {
    "describe_schema": (NoArgs, describe_schema, "List table definitions."),
    "run_sql": (SQLArgs, run_sql, "Run one read-only SQLite SELECT (max 1000 rows)."),
    "plot": (PlotArgs, plot, "Bar chart of a SELECT; x and y are result column names."),
    "export_csv": (ExportArgs, export_csv, "Write a SELECT result to a CSV file."),
}


def call_tool(name: str, args: Any) -> tuple[str, bool]:
    """Never raises: returns (text, is_error) so the model can recover."""
    try:
        model, fn, _ = TOOLS[name]
        out = fn(model(**args))
        out = out.model_dump() if isinstance(out, BaseModel) else out
        return json.dumps(out)[:20_000], False  # unserialisable output raises -> reported as a tool error
    except Exception as e:  # noqa: BLE001 - boundary: any tool failure becomes a tool_result
        return f"error: {e}", True
