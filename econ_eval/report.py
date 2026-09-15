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

TRACKS = ["quantitative", "reasoning", "coding", "writing", "finance", "review"]


def _load(db_path: Path, tracks: list[str] | None = None, models: list[str] | None = None):
    con = sqlite3.connect(db_path)
    sql = "SELECT task_id, track, model, score, passed, tokens_in, tokens_out FROM scores"
    where, params = [], []
    if tracks:
        where.append("track IN (%s)" % ",".join("?" * len(tracks)))
        params += list(tracks)
    if models:
        # model ids as stored in the DB; needed once contestants have run different
        # task sets (the 2026-09-15 five ran 50 tasks, the 2026-08-01 fleet 20)
        where.append("model IN (%s)" % ",".join("?" * len(models)))
        params += list(models)
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = con.execute(sql, tuple(params)).fetchall()
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


def build_report(db_path: Path, out_md: Path, out_png: Path,
                 tracks: list[str] | None = None, only_models: list[str] | None = None) -> None:
    scores, cost, correct = _load(db_path, tracks, only_models)
    models = sorted(scores.keys())
    lines = ["# econ-eval results", ""]
    if tracks:
        lines += [f"Tracks included: {', '.join(tracks)}.", ""]
    if only_models:
        lines += [f"Models included: {', '.join(only_models)}.", ""]

    # Overall per-model score with CI, best first
    lines += ["## Overall", "",
              "| model | score | 95% CI | total cost (USD) | cost/correct (USD) |",
              "|---|---|---|---|---|"]
    overall_means = {}
    overall_ci = {}
    for m in models:
        all_tasks = [t for tr in scores[m].values() for t in tr.values()]
        pt, lo, hi = stats.bootstrap_ci(all_tasks, iters=5000, seed=0)
        overall_means[m] = pt
        overall_ci[m] = (lo, hi)
    ranked = sorted(models, key=lambda m: overall_means[m], reverse=True)
    for m in ranked:
        lo, hi = overall_ci[m]
        cpc = cost[m] / correct[m] if correct[m] else float("nan")
        lines.append(f"| {m} | {overall_means[m]:.3f} | [{lo:.3f}, {hi:.3f}] "
                     f"| {cost[m]:.2f} | {cpc:.4f} |")
    lines.append("")

    # Per-track, best first
    for track in TRACKS:
        present = [m for m in models if track in scores[m]]
        if not present:
            continue
        rows = []
        for m in present:
            pt, lo, hi = stats.bootstrap_ci(_by_task(scores[m][track]), iters=5000, seed=0)
            rows.append((pt, lo, hi, m))
        rows.sort(reverse=True)
        lines += [f"## {track}", "", "| model | score | 95% CI |", "|---|---|---|"]
        for pt, lo, hi, m in rows:
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
    elif len(models) > 2:
        # Anchor: Opus 4.8 when it is in the set (the 2026-08-01 design); otherwise the
        # top-ranked model, so a filtered run (2026-09-15, five subscription models)
        # still gets a paired sign test against its leader.
        anchor = "claude-opus-4-8" if "claude-opus-4-8" in models else ranked[0]
        short = "opus" if anchor == "claude-opus-4-8" else anchor
        lines += [f"## Paired vs {short}", "",
                  f"| model | win-rate vs {short} | tasks | sign-test p | verdict |",
                  "|---|---|---|---|---|"]
        for m in ranked:
            if m == anchor:
                continue
            a_tasks, b_tasks = [], []
            for tr in TRACKS:
                for tid in scores[m].get(tr, {}):
                    if tid in scores[anchor].get(tr, {}):
                        a_tasks.append(scores[m][tr][tid])
                        b_tasks.append(scores[anchor][tr][tid])
            if not a_tasks:
                continue
            rate, n = stats.paired_winrate(a_tasks, b_tasks)
            p = stats.sign_test(a_tasks, b_tasks)
            if p >= 0.05:
                verdict = "no significant difference"
            else:
                verdict = f"beats {short}" if rate > 0.5 else f"loses to {short}"
            lines.append(f"| {m} | {rate:.2f} | {n} | {p:.4f} | {verdict} |")
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines))

    # Quality vs cost-per-correct scatter (log x: opus CLI cost dwarfs the cheap fleet)
    fig, ax = plt.subplots(figsize=(8, 5))
    for m in models:
        cpc = cost[m] / correct[m] if correct[m] else 0.0
        if cpc <= 0:
            continue
        ax.scatter(cpc, overall_means[m], s=80)
        ax.annotate(m.split("/")[-1], (cpc, overall_means[m]), xytext=(5, 5),
                    textcoords="offset points", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("cost per correct answer (USD, log scale)")
    ax.set_ylabel("mean score")
    ax.set_title("econ-eval: quality vs cost")
    ax.grid(True, alpha=0.3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
