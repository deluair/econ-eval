"""Live smoke: run one task end-to-end against both contestants + the judge.

Run: uv run python scripts/smoke.py [task_id]
Hits real endpoints (claude CLI, z.ai, deepseek). Use to confirm wiring and
that glm-5.2 is exposed before a full eval.
"""
from __future__ import annotations

import sys

from econ_eval import config
from econ_eval.models import Task
from econ_eval.runner import grade_sample


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "quant-hs6109-sum"
    path = config.TASKS_DIR / f"{task_id}.yaml"
    task = Task.from_yaml(path)
    models = config.build_models()
    judge = config.build_judge()
    print(f"task: {task.id} ({task.track})\n")
    for name, a in models.items():
        try:
            c = a.run(task.prompt)
            g = grade_sample(task, c.text, judge)
            print(f"[{name} / {a.model}] passed={g.passed} score={g.score:.2f} "
                  f"({g.detail}) latency={c.latency_s:.1f}s")
            print(f"  -> {c.text.strip()[:160]!r}\n")
        except Exception as e:
            print(f"[{name} / {a.model}] FAIL: {type(e).__name__}: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
