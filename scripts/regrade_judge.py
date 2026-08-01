"""Re-grade all judge-track rows in scores.sqlite with the current judge.

Completions are read back from transcript files (later occurrences win), so no
contestant is re-called. Rows whose completion text cannot be found are listed
and left untouched. Usage:

    uv run python scripts/regrade_judge.py transcripts-a.jsonl [more.jsonl ...]
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from econ_eval import config
from econ_eval.graders import judge as judge_mod
from econ_eval.models import Task

WORKERS = int(os.environ.get("REGRADE_WORKERS", "16"))
# Rows already carrying this marker are skipped, which makes the pass
# resumable. Changing judges means changing this string, so every row is
# regraded and no two judges ever share a scoreboard.
DONE_PREFIX = "opus5-judge"


def main(argv: list[str]) -> int:
    tasks = {t.id: t for p in sorted(config.TASKS_DIR.glob("*.yaml"))
             for t in [Task.from_yaml(p)]}
    judge_ids = {tid for tid, t in tasks.items() if t.grader["type"] == "judge"}

    texts: dict[tuple[str, str, int], str] = {}
    for path in argv:
        for line in open(path):
            r = json.loads(line)
            if r["task_id"] in judge_ids:
                texts[(r["task_id"], r["model"], r["idx"])] = r["completion"]

    con = sqlite3.connect(config.DB_PATH)
    con.execute("PRAGMA busy_timeout=60000")
    rows = con.execute(
        "SELECT task_id, model, idx FROM scores WHERE task_id IN (%s) "
        "AND (detail IS NULL OR detail NOT LIKE ?)"
        % ",".join("?" * len(judge_ids)), (*sorted(judge_ids), DONE_PREFIX + "%")
    ).fetchall()

    todo = [(t, m, i) for t, m, i in rows if (t, m, i) in texts]
    missing = [(t, m, i) for t, m, i in rows if (t, m, i) not in texts]
    print(f"judge-track rows not yet regraded: {len(rows)}, regradable: {len(todo)}, "
          f"missing transcripts: {len(missing)}")
    for key in missing:
        print("  MISSING", key)

    j = config.build_judge()

    def regrade(key):
        t, m, i = key
        g = judge_mod.rubric_score(j, tasks[t], texts[key])
        return key, g

    done = 0
    with ThreadPoolExecutor(WORKERS) as ex:
        for key, g in ex.map(regrade, todo):
            t, m, i = key
            con.execute(
                "UPDATE scores SET score=?, passed=?, detail=? "
                "WHERE task_id=? AND model=? AND idx=?",
                (g.score, int(g.passed), f"{DONE_PREFIX} {g.detail}", t, m, i))
            con.commit()
            done += 1
            if done % 25 == 0:
                print(f"  regraded {done}/{len(todo)}", flush=True)
    con.close()
    print(f"regraded {done} rows with {j.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
