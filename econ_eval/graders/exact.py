"""Normalized exact-match grader (objective)."""
from __future__ import annotations

from econ_eval.models import Grade, Task


def _norm(s: str) -> str:
    return " ".join(s.lower().replace(",", "").split())


def grade(task: Task, text: str) -> Grade:
    ref = _norm(str(task.grader["reference"]))
    passed = ref in _norm(text)
    return Grade(1.0 if passed else 0.0, passed, f"ref={ref!r}")
