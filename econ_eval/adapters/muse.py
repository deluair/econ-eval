"""Meta Muse Spark 1.3 via the Muse Code CLI (subscription) in headless mode.

`muse exec --json` streams JSONL events; the `run.terminal.completed` event
carries the final answer text. Token usage is not in that stream: the CLI
writes it to its own session store, one `model_completed` record per model
call, which is read back by the fixed `--session-id`. As with the Opus CLI
adapter, input_tokens include the whole Muse Code harness context (about 30k
per call), so Muse token/cost figures are an upper bound. Each call runs from
an empty scratch directory so no repository content leaks into the workspace.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import tempfile
import time
import uuid

MODEL = "muse-spark-1.3-contributor"
RETRIES = 3
SESSIONS = os.path.expanduser("~/.local/share/muse/sessions")
_SERVED = re.compile(r'"provider":"meta","request_id":"[^"]*","response_id":"[^"]*","model":"([^"]+)"')


def _parse_stream(stdout: str) -> tuple[str, str]:
    """Return (terminal_state, text) from the exec --json event stream."""
    terminal, text = "", ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("payload_type") == "run.terminal.completed":
            p = ev.get("payload", {})
            terminal = p.get("terminal", "")
            text = p.get("text") or ""
    return terminal, text


def _session_usage(session_id: str) -> tuple[dict, str]:
    """Sum usage over every model_completed record of the session; return (usage, model).

    The served model is the provider response's `model` (Muse Code 1.4.7 records
    the requested id, e.g. `muse-wonder-1.0`, in model_completed even when the
    contributor lane serves `muse-wonder-1.0-contributor`); model_completed is
    the fallback for older sessions.
    """
    total = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    model = served = ""
    for path in glob.glob(f"{SESSIONS}/*/*/*/{session_id}/session.jsonl"):
        for line in open(path):
            m = _SERVED.search(line)
            if m:
                served = m.group(1)
            if '"model_completed"' not in line:
                continue
            ev = json.loads(line).get("payload", {}).get("event", {})
            if ev.get("kind") != "model_completed":
                continue
            u = ev.get("usage", {}) or {}
            for k in total:
                total[k] += int(u.get(k, 0) or 0)
            model = ev.get("model") or model
    return total, served or model


class MuseAdapter:
    # A normal call takes 30 to 60 s. A call that hangs is one where the agent
    # proposed a tool call and is waiting for an approval that headless mode
    # never gives, so a short timeout plus the retry loop is the recovery path.
    def __init__(self, cli: str = "muse", timeout_s: int = 180,
                 name: str = "muse", model: str = MODEL,
                 request_model: str | None = None,
                 contributor_mode: str | None = None) -> None:
        self.cli = cli
        self.timeout_s = timeout_s
        self.name = name
        self.model = model
        # 2026-10-13 Wonder contestants: pin the requested model and the lane
        # (`--contributor-mode on` serves `<id>-contributor`, `off` the full model).
        self.request_model = request_model
        self.contributor_mode = contributor_mode
        self._workdir: str | None = None

    def _cwd(self) -> str:
        if self._workdir is None:
            self._workdir = tempfile.mkdtemp(prefix="econ-eval-muse-")
        return self._workdir

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        t0 = time.monotonic()
        for attempt in range(RETRIES):
            sid = str(uuid.uuid4())
            cmd = [self.cli, "exec", "--json", "--session-id", sid]
            if self.request_model:
                # 1.4.7 refuses a headless run in an undecided workspace; the
                # scratch dir is empty, so trusting it for the run is safe.
                cmd += ["--trust-workspace", "--model", self.request_model]
            if self.contributor_mode:
                cmd += ["--contributor-mode", self.contributor_mode]
            proc = subprocess.run(
                cmd + [prompt],
                cwd=self._cwd(), capture_output=True, text=True, timeout=self.timeout_s,
            )
            terminal, text = _parse_stream(proc.stdout)
            if proc.returncode == 0 and terminal == "completed":
                break
            if attempt == RETRIES - 1:
                raise RuntimeError(
                    f"muse CLI failed ({proc.returncode}, terminal={terminal!r}): "
                    f"{proc.stderr[-500:]}")
            time.sleep(10 * (attempt + 1))
        latency = time.monotonic() - t0
        usage, served = _session_usage(sid)
        if served and served != self.model:
            raise RuntimeError(f"muse served {served!r}, adapter expects {self.model!r}")
        return Completion(
            text=text,
            tokens_in=usage["input_tokens"],
            tokens_out=usage["output_tokens"],
            latency_s=latency,
            model=self.model,
            raw={"session_id": sid, "reasoning_tokens": usage["reasoning_tokens"]},
        )
