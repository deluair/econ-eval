"""Statistics: bootstrap CIs, paired win-rate, two-sided sign test.

Pure numpy; no scipy dependency. Deterministic given a seed.
"""
from __future__ import annotations

from math import comb

import numpy as np


def _task_means(scores_by_task: list[list[float]]) -> np.ndarray:
    return np.array([float(np.mean(t)) for t in scores_by_task], dtype=float)


def bootstrap_ci(scores_by_task: list[list[float]], iters: int = 10000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float, float]:
    """Mean over tasks of per-task means, with a percentile bootstrap CI.

    Resamples tasks with replacement; within each resampled task, resamples
    its samples with replacement.
    """
    rng = np.random.default_rng(seed)
    per_task = [np.asarray(t, dtype=float) for t in scores_by_task]
    n = len(per_task)
    point = float(np.mean([t.mean() for t in per_task]))
    boot = np.empty(iters)
    for b in range(iters):
        task_idx = rng.integers(0, n, n)
        vals = []
        for ti in task_idx:
            t = per_task[ti]
            vals.append(t[rng.integers(0, len(t), len(t))].mean())
        boot[b] = np.mean(vals)
    lo = float(np.percentile(boot, 100 * alpha / 2))
    hi = float(np.percentile(boot, 100 * (1 - alpha / 2)))
    return point, lo, hi


def paired_winrate(a_by_task: list[list[float]],
                   b_by_task: list[list[float]]) -> tuple[float, int]:
    """Fraction of tasks where A's mean score exceeds B's (ties excluded from wins)."""
    a = _task_means(a_by_task)
    b = _task_means(b_by_task)
    wins = int(np.sum(a > b))
    decided = int(np.sum(a != b))
    rate = wins / decided if decided else 0.5
    return rate, len(a)


def latency_summary(xs: list[float]) -> dict[str, float]:
    """n, mean, median, p95, min, max of per-sample latencies. Raises on empty."""
    a = np.asarray([float(x) for x in xs], dtype=float)
    if a.size == 0:
        raise ValueError("no latencies")
    return {
        "n": int(a.size),
        "mean": float(a.mean()),
        "median": float(np.median(a)),
        "p95": float(np.percentile(a, 95)),
        "min": float(a.min()),
        "max": float(a.max()),
    }


def check_latency_bars(medians: dict[str, float], bars: dict[str, float]) -> list[str]:
    """Sorted model names whose median latency exceeds their bar (models without rows ignored)."""
    return sorted(n for n, b in bars.items() if n in medians and medians[n] > b)


def sign_test(a_by_task: list[list[float]], b_by_task: list[list[float]]) -> float:
    """Two-sided exact binomial sign test p-value on per-task A>B vs A<B (ties dropped)."""
    a = _task_means(a_by_task)
    b = _task_means(b_by_task)
    pos = int(np.sum(a > b))
    neg = int(np.sum(a < b))
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    # two-sided: P(X <= k) + P(X >= n-k) under Binom(n, 0.5)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    p = min(1.0, 2 * tail)
    return float(p)
