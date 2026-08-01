"""OpenRouter adapter: one OpenAI-compatible endpoint, many vendors."""
from __future__ import annotations

import os
import time

API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Reasoning models spend output tokens on thinking before the visible answer,
# so the cap is much higher than the 4096 used for the direct adapters.
MAX_TOKENS = 16384
RETRIES = 3


class OpenRouterAdapter:
    def __init__(self, name: str, model: str) -> None:
        self.name = name
        self.model = model

    def _key(self) -> str:
        key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY (or OPENAI_API_KEY) is not set")
        return key

    def run(self, prompt: str) -> "Completion":
        import httpx

        from econ_eval.models import Completion

        t0 = time.monotonic()
        for attempt in range(RETRIES):
            try:
                r = httpx.post(
                    API_URL,
                    headers={"Authorization": f"Bearer {self._key()}"},
                    json={
                        "model": self.model,
                        "max_tokens": MAX_TOKENS,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=600.0,
                )
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"status {r.status_code}: {r.text[:200]}",
                        request=r.request, response=r,
                    )
                r.raise_for_status()
                data = r.json()
                if "choices" not in data:
                    raise RuntimeError(f"no choices in response: {str(data)[:200]}")
                break
            except (httpx.HTTPStatusError, httpx.TransportError, RuntimeError):
                if attempt == RETRIES - 1:
                    raise
                time.sleep(5 * (attempt + 1))
        latency = time.monotonic() - t0
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
        usage = data.get("usage") or {}
        return Completion(
            text=text,
            tokens_in=usage.get("prompt_tokens", 0) or 0,
            tokens_out=usage.get("completion_tokens", 0) or 0,
            latency_s=latency,
            model=self.model,
            raw={"id": data.get("id"), "finish_reason": choice.get("finish_reason")},
        )
