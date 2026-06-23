"""Build a markdown leaderboard + quality-vs-cost plot from scores.sqlite."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from econ_eval import stats
from econ_eval.config import PRICES

TRACKS = ["quantitative", "reasoning", "coding", "writing"]


def _load(db_path: Path):
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT task_id, track, model, score, passed, tokens_in, tokens_out FROM scores"
    ).fetchall()
    con.close()
    # scores[model][track][task_id] -> list of scores
    scores: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    cost = defaultdict(float)
    correct = defaultdict(int)
    for task_id, track, model, score, passed, ti, to in rows:
        scores[model][track][task_id].append(score)
        p = PRICES.get(model, {"in": 0, "out": 0})
        cost[model] += ti / 1e6 * p["in"] + to / 1e6 * p["out"]
        correct[model] += int(passed)
    return scores, cost, correct


def _by_task(model_scores: dict) -> list[list[float]]:
    return [v for v in model_scores.values()]


def build_report(db_path: Path, out_md: Path, out_png: Path) -> None:
    scores, cost, correct = _load(db_path)
    models = sorted(scores.keys())
    lines = ["# econ-eval results", ""]

    # Overall per-model score with CI
    lines += ["## Overall", "", "| model | score | 95% CI | cost/correct (USD) |",
              "|---|---|---|---|"]
    overall_means = {}
    for m in models:
        all_tasks = [t for tr in scores[m].values() for t in tr.values()]
        pt, lo, hi = stats.bootstrap_ci(all_tasks, iters=5000, seed=0)
        overall_means[m] = pt
        cpc = cost[m] / correct[m] if correct[m] else float("nan")
        lines.append(f"| {m} | {pt:.3f} | [{lo:.3f}, {hi:.3f}] | {cpc:.4f} |")
    lines.append("")

    # Per-track
    for track in TRACKS:
        present = [m for m in models if track in scores[m]]
        if not present:
            continue
        lines += [f"## {track}", "", "| model | score | 95% CI |", "|---|---|---|"]
        for m in present:
            pt, lo, hi = stats.bootstrap_ci(_by_task(scores[m][track]), iters=5000, seed=0)
            lines.append(f"| {m} | {pt:.3f} | [{lo:.3f}, {hi:.3f}] |")
        lines.append("")

    # Head-to-head (needs exactly two models)
    if len(models) == 2:
        a, b = models
        a_tasks, b_tasks = [], []
        for tr in TRACKS:
            for tid in scores[a].get(tr, {}):
                if tid in scores[b].get(tr, {}):
                    a_tasks.append(scores[a][tr][tid])
                    b_tasks.append(scores[b][tr][tid])
        rate, n = stats.paired_winrate(a_tasks, b_tasks)
        p = stats.sign_test(a_tasks, b_tasks)
        sig = "significant" if p < 0.05 else "NOT significant"
        leader = a if rate > 0.5 else (b if rate < 0.5 else "tie")
        lines += ["## Head-to-head", "",
                  f"- tasks compared: {n}",
                  f"- {a} win-rate vs {b}: {rate:.2f}",
                  f"- sign-test p-value: {p:.4f} ({sig} at alpha=0.05)",
                  f"- verdict: " + (
                      f"{leader} wins" if (p < 0.05 and leader != 'tie')
                      else "no significant difference"),
                  ""]

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines))

    # Quality vs cost-per-correct scatter
    fig, ax = plt.subplots(figsize=(6, 4))
    for m in models:
        cpc = cost[m] / correct[m] if correct[m] else 0.0
        ax.scatter(cpc, overall_means[m], s=80)
        ax.annotate(m, (cpc, overall_means[m]), xytext=(5, 5),
                    textcoords="offset points")
    ax.set_xlabel("cost per correct answer (USD)")
    ax.set_ylabel("mean score")
    ax.set_title("econ-eval: quality vs cost")
    ax.grid(True, alpha=0.3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
