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
PRICES = {
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},
    "glm-5.2": {"in": 0.6, "out": 2.2},
    "deepseek-v4-flash": {"in": 0.3, "out": 1.1},
}


def build_models():
    from econ_eval.adapters.opus import OpusAdapter
    from econ_eval.adapters.glm import GLMAdapter

    return {"opus": OpusAdapter(), "glm": GLMAdapter()}


def build_judge():
    from econ_eval.adapters.glm import DeepSeekAdapter

    return DeepSeekAdapter()
