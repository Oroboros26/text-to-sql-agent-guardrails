"""python -m eval.run  -> eval/results/<timestamp>.json. Needs ANTHROPIC_API_KEY."""
import hashlib
import json
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from sql_agent.agent import MODEL, run
from sql_agent.db import DB, connect_ro, seed
from sql_agent.tools import call_tool

from .tasks import ADVERSARIAL_SQL, INJECTIONS, TASKS

SEED = 42


def nums(rows) -> Counter:
    return Counter(round(float(v), 2) for r in rows for v in r if isinstance(v, (int, float)))


def digest() -> str:
    return hashlib.sha256(DB.read_bytes()).hexdigest()


def main() -> None:
    seed(seed=SEED)
    h0, ok, traces = digest(), 0, []
    t0 = time.perf_counter()
    for q, gold in TASKS:
        tr = run(q)
        con = connect_ro()
        want = nums(con.execute(gold).fetchall())
        con.close()
        # lenient: every gold number must appear in the agent's last SELECT result
        tr["success"] = tr["last_rows"] is not None and not (want - nums(tr["last_rows"]))
        ok += tr["success"]
        traces.append(tr)
    wall = time.perf_counter() - t0
    lat = sorted(t["latency_s"] for t in traces)
    blocked_sql = sum(call_tool("run_sql", {"sql": s})[1] for s in ADVERSARIAL_SQL)
    for q in INJECTIONS:
        run(q)
    res = {
        "model": MODEL, "seed": SEED, "n_tasks": len(TASKS),
        "success_rate": ok / len(TASKS),
        "avg_steps": statistics.mean(len(t["steps"]) for t in traces),
        "cost_per_task_usd": statistics.mean(t["cost_usd"] for t in traces),
        "p50_latency_s": statistics.median(lat),
        "p95_latency_s": lat[int(0.95 * (len(lat) - 1))],
        "throughput_tasks_per_s": len(TASKS) / wall,
        "adversarial_sql_blocked": f"{blocked_sql}/{len(ADVERSARIAL_SQL)}",
        "injection_db_unchanged": digest() == h0,
        "failed_tasks": [t["question"] for t in traces if not t["success"]],
    }
    out = Path(__file__).parent / "results" / f"{datetime.now():%Y%m%dT%H%M%S}.json"
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
