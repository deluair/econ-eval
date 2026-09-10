"""z.ai-style Anthropic-compatible adapters: GLM, DeepSeek (legacy judge), DeepSeek Flash."""
from __future__ import annotations

import os
import time

MAX_TOKENS = 4096


class ZAIAdapter:
    """Anthropic-SDK client pointed at an Anthropic-compatible base_url."""

    def __init__(self, name: str, model: str, base_url: str, key_env: str,
                 max_tokens: int = MAX_TOKENS) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url
        self.key_env = key_env
        self.max_tokens = max_tokens

    def _client(self):
        from anthropic import Anthropic

        key = os.environ.get(self.key_env)
        if not key:
            raise RuntimeError(f"{self.key_env} is not set")
        return Anthropic(base_url=self.base_url, api_key=key)

    def run(self, prompt: str) -> "Completion":
        from econ_eval.models import Completion

        client = self._client()
        t0 = time.monotonic()
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = time.monotonic() - t0
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        usage = getattr(msg, "usage", None)
        return Completion(
            text=text,
            tokens_in=getattr(usage, "input_tokens", 0) or 0,
            tokens_out=getattr(usage, "output_tokens", 0) or 0,
            latency_s=latency,
            model=self.model,
            raw={"id": getattr(msg, "id", None)},
        )


def GLMAdapter() -> ZAIAdapter:
    return ZAIAdapter("glm", "glm-5.2", "https://api.z.ai/api/anthropic", "ZAI_API_KEY")


def DeepSeekAdapter() -> ZAIAdapter:
    return ZAIAdapter(
        "deepseek", "deepseek-v4-flash", "https://api.deepseek.com/anthropic", "DEEPSEEK_API_KEY"
    )


def DeepSeekFlashAdapter() -> ZAIAdapter:
    """DeepSeek V4.1 Flash (released 2026-09-10) as a contestant, official endpoint.

    `deepseek-flash` is the vendor's canonical id for V4.1 Flash. Thinking is on
    by default and billed as output tokens, so the cap matches the OpenRouter
    fleet's 16384 rather than the 4096 used for GLM.
    """
    return ZAIAdapter(
        "deepseek-flash", "deepseek-flash", "https://api.deepseek.com/anthropic",
        "DEEPSEEK_API_KEY", max_tokens=16384,
    )
