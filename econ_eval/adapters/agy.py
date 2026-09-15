"""Gemini via the Antigravity CLI (agy) in headless print mode, Google AI Ultra plan.

`agy -p --output-format json` returns one JSON object: `status` (SUCCESS/ERROR),
`response` (final text), `usage.input_tokens` / `usage.output_tokens`. Input tokens
include the agy harness context (about 13k per call, measured 2026-09-15), so token
figures are an upper bound like the Claude CLI rows. Gemini 3.8 Flash is served only
through this subscription (not on the Gemini API, verified 2026-08-21), so the cost
column is notional. Each call runs from an empty scratch directory; the prompt is
text-only, so no tool permissions are needed.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import time

MODEL = "gemini-3.8-flash-high"
RETRIES = 3
# agy is an agent harness: on "return only the code" prompts Gemini tried to read or
# write workspace files, print mode auto-denied the tool call, and the reply came back
# empty (`denied_actions: read_file`, reproduced 2026-09-15). The preamble keeps the
# answer in the reply, the same accommodation the Muse adapter needed.
PREAMBLE = ("Answer directly in this reply. Do not read, create or edit any file and do not "
            "run any command; there is no workspace. Put the complete answer in the message.\n\n")


class AgyAdapter:
    def __init__(self, cli: str = "agy", timeout_s: int = 300,
                 name: str = "gemini-3.8-flash", model: str = MODEL) -> None:
        self.cli = cli
        self.timeout_s = timeout_s
        self.name = name
        self.model = model
        self._workdir: str | None = None

    def _cwd(self) -> str:
        if self._workdir is None:
            self._workdir = tempfile.mkdtemp(prefix="econ-eval-agy-")
        return self._workdir

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        t0 = time.monotonic()
        err = ""
        for attempt in range(RETRIES):
            proc = subprocess.run(
                [self.cli, "-p", PREAMBLE + prompt, "--output-format", "json", "--model", self.model,
                 "--disable-slash-commands"],
                capture_output=True, text=True, timeout=self.timeout_s,
                cwd=self._cwd(), stdin=subprocess.DEVNULL,
            )
            data = _parse(proc.stdout)
            # A 503 "No capacity" comes back as status ERROR with the text still filled;
            # treat anything but SUCCESS as a failed attempt.
            if proc.returncode == 0 and data.get("status") == "SUCCESS":
                usage = data.get("usage", {}) or {}
                return Completion(
                    text=data.get("response", "") or "",
                    tokens_in=int(usage.get("input_tokens", 0)),
                    tokens_out=int(usage.get("output_tokens", 0)),
                    latency_s=time.monotonic() - t0,
                    model=self.model,
                    raw={"usage": usage, "conversation_id": data.get("conversation_id")},
                )
            err = data.get("error") or proc.stderr[:500] or f"exit {proc.returncode}"
            time.sleep(15 * (attempt + 1))
        raise RuntimeError(f"agy failed after {RETRIES} attempts: {err}")


def _parse(stdout: str) -> dict:
    s = stdout.strip()
    if not s:
        return {}
    # the routine-card hook may print text above the JSON object; take the last object
    start = s.rfind("\n{")
    s = s[start + 1:] if start >= 0 else s
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {}
