"""Runtime configuration and registries."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results"
DB_PATH = RESULTS_DIR / "scores.sqlite"

DEFAULT_SAMPLES = 5

# Rough per-1M-token prices (USD) for the cost-per-correct figure.
# Opus 4.8 from the model catalog; GLM is the cheap z.ai consult tier.
# OpenRouter prices read from https://openrouter.ai/api/v1/models on 2026-07-31.
# deepseek-flash (V4.1 Flash): official off-peak cache-miss price from
# api-docs.deepseek.com/quick_start/pricing on 2026-09-10 (peak is 2x).
# muse-spark-1.3-contributor: Meta contributor API price (also the OpenRouter
# catalog figure, 2026-09-10); the run itself goes through the Muse Code
# subscription, so like Opus the cost column is notional.
PRICES = {
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},
    # 2026-09-15 additions. Fable 5.1: Anthropic API list price (claude-api skill
    # model table, cached 2026-06-24). gpt-6-astra and gemini-3.8-flash-high are served
    # only through the ChatGPT and Google AI Ultra subscriptions (no API price exists),
    # so their cost column is 0 and the README says "subscription".
    "claude-fable-5-1": {"in": 10.0, "out": 50.0},
    "gpt-6-astra": {"in": 0.0, "out": 0.0},
    "gemini-3.8-flash-high": {"in": 0.0, "out": 0.0},
    "glm-5.2": {"in": 0.6, "out": 2.2},
    "deepseek-v4-flash": {"in": 0.3, "out": 1.1},
    "deepseek-flash": {"in": 0.15, "out": 0.6},
    "muse-spark-1.3-contributor": {"in": 0.1, "out": 0.2},
    "google/gemini-3.6-flash": {"in": 1.5, "out": 7.5},
    "deepseek/deepseek-v4-flash-0731": {"in": 0.14, "out": 0.28},
    "moonshotai/kimi-k3": {"in": 3.0, "out": 15.0},
    "nvidia/nemotron-3-ultra-550b-a55b": {"in": 0.6, "out": 3.6},
    "minimax/minimax-m3": {"in": 0.3, "out": 1.2},
    "openai/gpt-5.6-luna": {"in": 0.1, "out": 0.6},
    "x-ai/grok-4.5": {"in": 2.0, "out": 6.0},
    "meta-llama/llama-4-maverick": {"in": 0.2, "out": 0.8},
}

# Cheap-model fleet served through one OpenRouter endpoint.
OPENROUTER_MODELS = {
    "gemini-flash": "google/gemini-3.6-flash",
    "deepseek-0731": "deepseek/deepseek-v4-flash-0731",
    "kimi-k3": "moonshotai/kimi-k3",
    "nemotron-ultra": "nvidia/nemotron-3-ultra-550b-a55b",
    "minimax-m3": "minimax/minimax-m3",
    "luna": "openai/gpt-5.6-luna",
    "grok": "x-ai/grok-4.5",
    "llama": "meta-llama/llama-4-maverick",
}


def build_models(only: set[str] | None = None):
    from econ_eval.adapters.opus import OpusAdapter
    from econ_eval.adapters.glm import GLMAdapter, DeepSeekFlashAdapter
    from econ_eval.adapters.openrouter import OpenRouterAdapter
    from econ_eval.adapters.muse import MuseAdapter
    from econ_eval.adapters.agy import AgyAdapter
    from econ_eval.adapters.codex import CodexAdapter

    models = {"opus": OpusAdapter(), "glm": GLMAdapter(), "deepseek-flash": DeepSeekFlashAdapter(),
              "muse": MuseAdapter(),
              # 2026-09-15 contestants: subscription CLIs, see each adapter's docstring.
              "fable": OpusAdapter(name="fable", model="claude-fable-5-1", timeout_s=600),
              "astra": CodexAdapter(),
              "gemini-3.8-flash": AgyAdapter()}
    for name, model_id in OPENROUTER_MODELS.items():
        models[name] = OpenRouterAdapter(name, model_id)
    if only is not None:
        unknown = only - models.keys()
        if unknown:
            raise ValueError(f"unknown model names: {sorted(unknown)}")
        models = {k: v for k, v in models.items() if k in only}
    return models


def build_judge():
    import os

    if os.environ.get("JUDGE", "opus") == "astra":
        from econ_eval.adapters.codex import CodexAdapter

        return CodexAdapter(name="judge-astra")
    from econ_eval.adapters.opus import JudgeAdapter

    return JudgeAdapter()
