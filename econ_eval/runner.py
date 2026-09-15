"""Runner: tasks x models x N samples -> graded, cached, resumable results."""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from econ_eval.graders import numeric, exact, code_exec, judge as judge_mod
from econ_eval.graders import artifact as artifact_mod
from econ_eval.models import Grade, Task

SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
  task_id TEXT, track TEXT, model TEXT, idx INTEGER,
  score REAL, passed INTEGER, tokens_in INTEGER, tokens_out INTEGER,
  latency_s REAL, detail TEXT,
  PRIMARY KEY (task_id, model, idx)
);
"""


def grade_sample(task: Task, text: str, judge, workdir=None) -> Grade:
    gt = task.grader["type"]
    if gt == "numeric":
        return numeric.grade(task, text)
    if gt == "exact":
        return exact.grade(task, text)
    if gt == "code_exec":
        return code_exec.grade(task, text)
    if gt == "judge":
        return judge_mod.rubric_score(judge, task, text)
    if gt == "artifact":
        return artifact_mod.grade(task, text, workdir)
    raise ValueError(f"unknown grader type {gt!r}")


def _seed_workdir(task: Task, workdir: Path) -> None:
    """Copy task seed files (tasks/files/<id>/[files]) into the workdir."""
    from econ_eval.config import TASKS_DIR

    seed = TASKS_DIR / "files" / task.id
    if task.files:
        seed = seed / task.files
    if seed.is_dir():
        shutil.copytree(seed, workdir, dirs_exist_ok=True)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA busy_timeout=60000")
    con.executescript(SCHEMA)
    return con


def _cached(con, task_id, model, idx) -> bool:
    cur = con.execute(
        "SELECT 1 FROM scores WHERE task_id=? AND model=? AND idx=?",
        (task_id, model, idx),
    )
    return cur.fetchone() is not None


def run(tasks: list[Task], models: dict, judge, n: int,
        transcripts_path: Path, db_path: Path,
        dry_run: bool = False, only_task: str | None = None) -> int:
    if only_task:
        tasks = [t for t in tasks if t.id == only_task]
    total_calls = sum(min(n, t.samples) for t in tasks) * len(models)
    print(f"tasks={len(tasks)} models={len(models)} samples<={n} -> up to {total_calls} model calls")
    if dry_run:
        print("dry-run: no calls made")
        return 0

    con = _connect(db_path)
    transcripts_path.parent.mkdir(parents=True, exist_ok=True)
    made = 0
    with open(transcripts_path, "a") as tf:
        for task in tasks:
            k = min(n, task.samples)
            for mname, adapter in models.items():
                for idx in range(k):
                    if _cached(con, task.id, adapter.model, idx):
                        continue
                    if task.track == "agent":
                        from econ_eval.agent_loop import run_agent

                        with tempfile.TemporaryDirectory(prefix=f"agent-{task.id}-") as wd:
                            _seed_workdir(task, Path(wd))
                            comp = run_agent(
                                adapter, task.prompt, wd,
                                max_steps=int(task.grader.get("max_steps", 12)),
                            )
                            g = grade_sample(task, comp.text, judge, workdir=wd)
                    else:
                        comp = adapter.run(task.prompt)
                        g = grade_sample(task, comp.text, judge)
                    con.execute(
                        "INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (task.id, task.track, adapter.model, idx, g.score,
                         int(g.passed), comp.tokens_in, comp.tokens_out,
                         comp.latency_s, g.detail),
                    )
                    con.commit()
                    tf.write(json.dumps({
                        "ts": time.time(), "task_id": task.id, "track": task.track,
                        "model": adapter.model, "idx": idx, "prompt": task.prompt,
                        "completion": comp.text, "score": g.score, "passed": g.passed,
                        "detail": g.detail, "trace": comp.raw.get("trace"),
                    }) + "\n")
                    made += 1
    con.close()
    print(f"made {made} new model calls")
    return made
