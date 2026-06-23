"""Numeric-tolerance grader (objective)."""
from __future__ import annotations

import re

from econ_eval.models import Grade, Task

_NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")


def extract_number(text: str) -> float | None:
    # Prefer an explicit "ANSWER:" line if present.
    for line in reversed(text.splitlines()):
        if "answer" in line.lower():
            m = _NUM.findall(line)
            if m:
                return _to_float(m[-1])
    m = _NUM.findall(text)
    return _to_float(m[-1]) if m else None


def _to_float(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def grade(task: Task, text: str) -> Grade:
    ref = float(task.grader["reference"])
    tol = float(task.grader.get("tolerance_pct", 0.5)) / 100.0
    got = extract_number(text)
    if got is None:
        return Grade(0.0, False, "no number found")
    rel = abs(got - ref) / ref if ref != 0 else abs(got)
    passed = rel <= tol
    return Grade(1.0 if passed else 0.0, passed, f"got={got} ref={ref} rel={rel:.4f}")
