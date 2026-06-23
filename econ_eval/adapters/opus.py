"""Claude Opus 4.8 via the Claude Code CLI in headless print mode."""
from __future__ import annotations

import json
import subprocess
import time

MODEL = "claude-opus-4-8"


class OpusAdapter:
    name = "opus"
    model = MODEL

    def __init__(self, cli: str = "claude", timeout_s: int = 300) -> None:
        self.cli = cli
        self.timeout_s = timeout_s

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        t0 = time.monotonic()
        proc = subprocess.run(
            [self.cli, "-p", prompt, "--output-format", "json"],
            capture_output=True, text=True, timeout=self.timeout_s,
        )
        latency = time.monotonic() - t0
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({proc.returncode}): {proc.stderr[:500]}")
        env = json.loads(proc.stdout)
        usage = env.get("usage", {}) or {}
        return Completion(
            text=env.get("result", ""),
            tokens_in=int(usage.get("input_tokens", 0)),
            tokens_out=int(usage.get("output_tokens", 0)),
            latency_s=latency,
            model=self.model,
            raw=env,
        )
