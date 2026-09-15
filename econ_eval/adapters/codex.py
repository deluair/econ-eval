"""OpenAI via the Codex CLI on the ChatGPT plan, headless `codex exec --json`.

The event stream is JSONL: `item.completed` with `item.type == "agent_message"`
carries answer text (the last one is the final answer), `turn.completed` carries
`usage.input_tokens` / `usage.output_tokens` (input includes about 25k of Codex
harness context per call, measured 2026-09-15; cached_input_tokens is reported
separately). GPT-6 Astra is served on the plan only, so the cost column is
notional. Runs from an empty scratch directory with the default read-only sandbox.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import time

MODEL = "gpt-6-astra"
RETRIES = 3


def _parse(stdout: str) -> tuple[str, dict]:
    text, usage = "", {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "item.completed":
            item = ev.get("item", {}) or {}
            if item.get("type") == "agent_message":
                text = item.get("text") or text
        elif ev.get("type") == "turn.completed":
            usage = ev.get("usage", {}) or {}
    return text, usage


class CodexAdapter:
    def __init__(self, cli: str = "codex", timeout_s: int = 600,
                 name: str = "astra", model: str = MODEL,
                 reasoning_effort: str = "high") -> None:
        self.cli = cli
        self.timeout_s = timeout_s
        self.name = name
        self.model = model
        self.reasoning_effort = reasoning_effort
        self._workdir: str | None = None

    def _cwd(self) -> str:
        if self._workdir is None:
            self._workdir = tempfile.mkdtemp(prefix="econ-eval-codex-")
        return self._workdir

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        t0 = time.monotonic()
        err = ""
        for attempt in range(RETRIES):
            proc = subprocess.run(
                [self.cli, "exec", "--skip-git-repo-check", "--json", "-m", self.model,
                 "-c", f"model_reasoning_effort={self.reasoning_effort}",
                 "-C", self._cwd(), prompt],
                capture_output=True, text=True, timeout=self.timeout_s,
                cwd=self._cwd(), stdin=subprocess.DEVNULL,
            )
            text, usage = _parse(proc.stdout)
            if proc.returncode == 0 and text:
                return Completion(
                    text=text,
                    tokens_in=int(usage.get("input_tokens", 0)),
                    tokens_out=int(usage.get("output_tokens", 0)),
                    latency_s=time.monotonic() - t0,
                    model=self.model,
                    raw={"usage": usage},
                )
            err = proc.stderr[-500:] or f"exit {proc.returncode}, no agent_message"
            time.sleep(15 * (attempt + 1))
        raise RuntimeError(f"codex failed after {RETRIES} attempts: {err}")
