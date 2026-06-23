"""Code-execution grader: run model code + task assertions in a subprocess."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from econ_eval.models import Grade, Task


def _extract_code(text: str) -> str:
    if "```" in text:
        parts = text.split("```")
        # take the largest fenced block, stripping an optional language tag
        blocks = []
        for i in range(1, len(parts), 2):
            b = parts[i]
            if "\n" in b:
                b = b.split("\n", 1)[1]
            blocks.append(b)
        if blocks:
            return max(blocks, key=len)
    return text


def grade(task: Task, text: str) -> Grade:
    code = _extract_code(text)
    assertions = task.grader.get("assertions", "")
    timeout_s = int(task.grader.get("timeout_s", 20))
    script = code + "\n\n# --- task assertions ---\n" + assertions + "\n"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "candidate.py"
        p.write_text(script)
        try:
            proc = subprocess.run(
                ["uv", "run", "python", str(p)],
                capture_output=True, text=True, timeout=timeout_s, cwd=d,
            )
        except subprocess.TimeoutExpired:
            return Grade(0.0, False, "timeout")
    passed = proc.returncode == 0
    detail = "ok" if passed else (proc.stderr.strip().splitlines() or ["error"])[-1]
    return Grade(1.0 if passed else 0.0, passed, detail[:200])
