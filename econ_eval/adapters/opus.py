"""Claude Opus 4.8 via the Claude Code CLI in headless print mode.

The CLI emits `--output-format json` as a JSON array of stream events; the
final element with type=="result" carries the answer text and usage. Note:
the reported input_tokens include the full Claude Code harness context (tools,
skills, memory), so Opus token/cost figures are an upper bound and are NOT
directly comparable to GLM's bare API-call tokens. See README cost caveat.
"""
from __future__ import annotations

import json
import subprocess
import time

MODEL = "claude-opus-4-8"
RETRIES = 3


def _parse(stdout: str):
    env = json.loads(stdout)
    if isinstance(env, dict):
        u = env.get("usage", {}) or {}
        return env.get("result", ""), u
    # array of stream events
    result_el = next(
        (e for e in reversed(env) if isinstance(e, dict) and e.get("type") == "result"),
        None,
    )
    if result_el is not None:
        return result_el.get("result", ""), (result_el.get("usage", {}) or {})
    asst = [e for e in env if isinstance(e, dict) and e.get("type") == "assistant"]
    if asst:
        msg = asst[-1].get("message", {})
        text = "".join(
            b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text"
        )
        return text, (msg.get("usage", {}) or {})
    return "", {}


class OpusAdapter:
    def __init__(self, cli: str = "claude", timeout_s: int = 300,
                 name: str = "opus", model: str = MODEL) -> None:
        self.cli = cli
        self.timeout_s = timeout_s
        self.name = name
        self.model = model

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        t0 = time.monotonic()
        # The CLI intermittently exits non-zero under concurrent invocation, so
        # a failed call is retried with backoff before giving up.
        for attempt in range(RETRIES):
            proc = subprocess.run(
                [self.cli, "-p", prompt, "--output-format", "json", "--model", self.model],
                capture_output=True, text=True, timeout=self.timeout_s,
            )
            if proc.returncode == 0:
                break
            if attempt == RETRIES - 1:
                raise RuntimeError(
                    f"claude CLI failed ({proc.returncode}): {proc.stderr[:500]}")
            time.sleep(10 * (attempt + 1))
        latency = time.monotonic() - t0
        text, usage = _parse(proc.stdout)
        return Completion(
            text=text,
            tokens_in=int(usage.get("input_tokens", 0)),
            tokens_out=int(usage.get("output_tokens", 0)),
            latency_s=latency,
            model=self.model,
            raw={"usage": usage},
        )


def FableJudgeAdapter() -> OpusAdapter:
    """Fable 5 as judge, same CLI subscription path as opus (not OpenRouter)."""
    return OpusAdapter(name="fable", model="claude-fable-5", timeout_s=600)
