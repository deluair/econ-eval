"""Artifact grader for `agent`-track tasks: grade files left in the workdir.

Two modes, selected by ``grader.mode``:

- ``numeric-on-file``: read ``grader.file`` (relative to the workdir),
  find the last number matching ``grader.pattern`` (a regex with an
  optional capture group; defaults to the numeric grader's number
  pattern), and compare against ``grader.reference`` within
  ``grader.tolerance_pct`` percent — the same relative-error rule as
  the numeric grader.
- ``assertions-on-file``: run ``grader.assertions`` (a Python snippet)
  with the workdir as cwd, code_exec style; exit 0 passes.

The workdir is passed explicitly by the runner (``grade(task, text,
workdir)``); ``text`` is ignored except in the failure detail.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from econ_eval.graders import numeric as numeric_mod
from econ_eval.models import Grade, Task


def _resolve(workdir, rel: str) -> Path:
    if workdir is None:
        raise ValueError("artifact grader needs a workdir")
    p = (Path(workdir) / rel).resolve()
    base = Path(workdir).resolve()
    if p != base and base not in p.parents:
        raise ValueError(f"path escapes workdir: {rel!r}")
    return p


def _grade_numeric(task: Task, workdir) -> Grade:
    g = task.grader
    rel = g.get("file")
    if not rel:
        return Grade(0.0, False, "artifact grader needs `file:`")
    ref = float(g["reference"])
    tol = float(g.get("tolerance_pct", 0.5)) / 100.0
    try:
        content = _resolve(workdir, rel).read_text()
    except (ValueError, OSError) as e:
        return Grade(0.0, False, f"cannot read {rel}: {e}"[:200])
    pattern = g.get("pattern")
    if pattern:
        try:
            matches = re.findall(pattern, content)
        except re.error as e:
            return Grade(0.0, False, f"bad pattern: {e}"[:200])
        if not matches:
            return Grade(0.0, False, f"pattern found no match in {rel}")
        raw = matches[-1] if isinstance(matches[-1], str) else matches[-1][0]
        try:
            got = float(raw.replace(",", ""))
        except ValueError:
            return Grade(0.0, False, f"match {raw!r} is not a number")
    else:
        got = numeric_mod.extract_number(content)
        if got is None:
            return Grade(0.0, False, f"no number found in {rel}")
    rel_err = abs(got - ref) / ref if ref != 0 else abs(got)
    passed = rel_err <= tol
    return Grade(1.0 if passed else 0.0, passed, f"got={got} ref={ref} rel={rel_err:.4f}")


def _grade_assertions(task: Task, workdir) -> Grade:
    g = task.grader
    assertions = g.get("assertions", "")
    if not assertions.strip():
        return Grade(0.0, False, "artifact grader needs `assertions:`")
    if workdir is None:
        return Grade(0.0, False, "artifact grader needs a workdir")
    timeout_s = int(g.get("timeout_s", 20))
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir=workdir, delete=False) as f:
        f.write(assertions + "\n")
        target = f.name
    try:
        proc = subprocess.run(
            ["uv", "run", "python", target],
            capture_output=True, text=True, timeout=timeout_s, cwd=workdir,
        )
    except subprocess.TimeoutExpired:
        return Grade(0.0, False, "timeout")
    passed = proc.returncode == 0
    detail = "ok" if passed else (proc.stderr.strip().splitlines() or ["error"])[-1]
    return Grade(1.0 if passed else 0.0, passed, detail[:200])


def grade(task: Task, text: str, workdir=None) -> Grade:
    mode = task.grader.get("mode", "numeric-on-file")
    if mode == "numeric-on-file":
        return _grade_numeric(task, workdir)
    if mode == "assertions-on-file":
        return _grade_assertions(task, workdir)
    return Grade(0.0, False, f"unknown artifact mode {mode!r}")
