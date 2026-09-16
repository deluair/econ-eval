"""Export the benchmark to a Hugging Face dataset folder and a static Space.

Reads tasks/*.yaml, results/scores.sqlite, the plots, and every transcript
file it can find (results/ plus the Google Drive backup), re-derives both
leaderboards with econ_eval.stats (same bootstrap, same sign test as
`make report`), and writes:

  <out>/dataset/   tasks.jsonl, scores.csv, transcripts.jsonl,
                   leaderboard_20task.csv, leaderboard_50task.csv,
                   tracks_20task.csv, tracks_50task.csv, plots, README.md
  <out>/space/     index.html (leaderboard page, data embedded), README.md

Every number in the two cards is rendered from the computed tables, never
typed. Usage:

  uv run python scripts/export_hf.py --out /path/to/export \
      [--transcripts DIR ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from econ_eval import stats
from econ_eval.config import PRICES
from econ_eval.models import Task
from econ_eval.report import TRACKS, _by_task

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "results" / "scores.sqlite"

# The two runs on record. A: 20 original tasks, 12 models, one judge (Opus 5).
# B: 50 tasks, the five 2026-09-15 contestants, judge GPT-6 Astra for every
# row that was not already cached from the Opus-5-judged 2026-09-10 run.
RUN_A_MODELS = [
    "deepseek-flash", "claude-opus-4-8", "moonshotai/kimi-k3",
    "muse-spark-1.3-contributor", "google/gemini-3.6-flash", "openai/gpt-5.6-luna",
    "x-ai/grok-4.5", "deepseek/deepseek-v4-flash-0731", "minimax/minimax-m3",
    "nvidia/nemotron-3-ultra-550b-a55b", "glm-5.2", "meta-llama/llama-4-maverick",
]
RUN_B_MODELS = [
    "gpt-6-astra", "gemini-3.8-flash-high", "muse-spark-1.3-contributor",
    "deepseek-flash", "claude-fable-5-1",
]
RUN_A_DATE = "2026-09-10"
RUN_B_DATE = "2026-09-15"
OPUS5_PREFIX = "opus5-judge "
HF_DATASET = "deluair/econ-eval"
HF_SPACE = "deluair/econ-eval"
GITHUB = "https://github.com/deluair/econ-eval"

# Display labels: the sqlite `model` column is the adapter's stored id.
LABEL = {
    "deepseek-flash": "DeepSeek V4.1 Flash",
    "claude-opus-4-8": "Claude Opus 4.8",
    "moonshotai/kimi-k3": "Kimi K3",
    "muse-spark-1.3-contributor": "Meta Muse Spark 1.3",
    "google/gemini-3.6-flash": "Gemini 3.6 Flash",
    "openai/gpt-5.6-luna": "GPT-5.6 Luna",
    "x-ai/grok-4.5": "Grok 4.5",
    "deepseek/deepseek-v4-flash-0731": "DeepSeek V4 Flash (0731)",
    "minimax/minimax-m3": "MiniMax M3",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B",
    "glm-5.2": "GLM 5.2",
    "meta-llama/llama-4-maverick": "Llama 4 Maverick",
    "gpt-6-astra": "GPT-6 Astra",
    "gemini-3.8-flash-high": "Gemini 3.8 Flash (high)",
    "claude-fable-5-1": "Claude Fable 5.1",
}
SUBSCRIPTION_ONLY = {"gpt-6-astra", "gemini-3.8-flash-high"}


# ----------------------------------------------------------------- tasks

def load_tasks() -> list[Task]:
    return [Task.from_yaml(p) for p in sorted((ROOT / "tasks").glob("*.yaml"))]


def task_rows(tasks: list[Task]) -> list[dict]:
    rows = []
    for t in tasks:
        g = t.grader
        files = []
        fdir = ROOT / "tasks" / "files" / t.id
        if fdir.is_dir():
            for f in sorted(fdir.iterdir()):
                files.append({"name": f.name, "content": f.read_text()})
        rows.append({
            "id": t.id,
            "track": t.track,
            "prompt": t.prompt,
            "grader_type": g.get("type"),
            "reference": "" if g.get("reference") is None else str(g.get("reference")),
            "tolerance_pct": g.get("tolerance_pct"),
            "rubric": list(g.get("rubric", [])),
            "grader_json": json.dumps(g, ensure_ascii=False),
            "source": t.source,
            "samples": t.samples,
            "files_json": json.dumps(files, ensure_ascii=False) if files else "",
        })
    return rows


# ---------------------------------------------------------------- scores

def score_rows(tasks: list[Task]) -> list[dict]:
    gtype = {t.id: t.grader.get("type") for t in tasks}
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    orig20 = {r[0] for r in con.execute(
        "SELECT DISTINCT task_id FROM scores WHERE model='claude-opus-4-8'")}
    assert len(orig20) == 20, len(orig20)
    rows = []
    for r in con.execute("SELECT * FROM scores ORDER BY model, task_id, idx"):
        d = dict(r)
        if d["task_id"] not in gtype:
            raise SystemExit(f"score row for unknown task {d['task_id']}")
        judged = gtype[d["task_id"]] == "judge"
        if not judged:
            judge = "deterministic"
        elif d["detail"].startswith(OPUS5_PREFIX):
            judge = "claude-opus-5"
        elif d["model"] in RUN_B_MODELS:
            judge = "gpt-6-astra"
        else:
            raise SystemExit(f"unlabelled judge row {d['model']} {d['task_id']} {d['idx']}")
        d["judge"] = judge
        d["task_set"] = ("original-20" if d["task_id"] in orig20
                         else "agent-pilot" if d["track"] == "agent" else "daily-work-30")
        rows.append(d)
    con.close()
    return rows


# ------------------------------------------------------------ leaderboard

def _load_tasks(models: list[str], task_ids: set[str]):
    """report._load restricted to a task set: run A models also hold 50-task rows."""
    con = sqlite3.connect(DB)
    m_q, t_q = ",".join("?" * len(models)), ",".join("?" * len(TRACKS))
    q = ("SELECT task_id, track, model, score, passed, tokens_in, tokens_out FROM scores "
         f"WHERE model IN ({m_q}) AND track IN ({t_q})")
    rows = con.execute(q, (*models, *TRACKS)).fetchall()
    con.close()
    scores: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    cost = defaultdict(float)
    correct = defaultdict(int)
    for task_id, track, model, score, passed, ti, to in rows:
        if task_id not in task_ids:
            continue
        scores[model][track][task_id].append(score)
        p = PRICES.get(model, {"in": 0, "out": 0})
        cost[model] += ti / 1e6 * p["in"] + to / 1e6 * p["out"]
        correct[model] += int(passed)
    return scores, cost, correct


def leaderboard(models: list[str], anchor: str, task_ids: set[str]) -> tuple[list[dict], list[dict]]:
    """Overall table + per-track table, same arithmetic as report.build_report."""
    scores, cost, correct = _load_tasks(models, task_ids)
    overall = {}
    for m in models:
        all_tasks = [t for tr in scores[m].values() for t in tr.values()]
        pt, lo, hi = stats.bootstrap_ci(all_tasks, iters=5000, seed=0)
        overall[m] = (pt, lo, hi, len(all_tasks), sum(len(t) for t in all_tasks))
    ranked = sorted(models, key=lambda m: overall[m][0], reverse=True)
    table = []
    for rank, m in enumerate(ranked, 1):
        pt, lo, hi, ntask, nrow = overall[m]
        cpc = cost[m] / correct[m] if correct[m] else 0.0
        if m == anchor:
            p, rate, verdict = None, None, "reference"
        else:
            a_t, b_t = [], []
            for tr in TRACKS:
                for tid in scores[m].get(tr, {}):
                    if tid in scores[anchor].get(tr, {}):
                        a_t.append(scores[m][tr][tid])
                        b_t.append(scores[anchor][tr][tid])
            rate, _ = stats.paired_winrate(a_t, b_t)
            p = stats.sign_test(a_t, b_t)
            if p >= 0.05:
                verdict = "tied"
            else:
                verdict = "beats" if rate > 0.5 else "loses"
        table.append({
            "rank": rank, "model": m, "label": LABEL[m],
            "score": round(pt, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
            "tasks": ntask, "completions": nrow,
            "total_cost_usd": round(cost[m], 4),
            "cost_per_correct_usd": round(cpc, 6),
            "cost_basis": ("subscription, no API price" if m in SUBSCRIPTION_ONLY
                           else "API list price x measured tokens"),
            "sign_test_p_vs_anchor": None if p is None else round(p, 4),
            "verdict_vs_anchor": verdict,
        })
    tracks = []
    for m in ranked:
        row = {"model": m, "label": LABEL[m]}
        for tr in TRACKS:
            if tr in scores[m]:
                pt, lo, hi = stats.bootstrap_ci(_by_task(scores[m][tr]), iters=5000, seed=0)
                row[tr] = round(pt, 3)
            else:
                row[tr] = None
        tracks.append(row)
    return table, tracks


# ------------------------------------------------------------ transcripts

def collect_transcripts(dirs: list[Path], current: dict) -> list[dict]:
    """Merge transcript files; score fields come from scores.sqlite, not the file.

    June 2026 judge rows were regraded by Opus 5 on 2026-08-01, so a transcript's
    own score field can be stale. `current` maps (model, task_id, idx) to the
    live (score, passed, detail); a transcript without a live row is dropped.
    """
    seen, out = set(), []
    files = []
    for d in dirs:
        files += sorted(d.glob("transcripts-*.jsonl"))
    for f in files:
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            key = (d["model"], d["task_id"], d["idx"])
            if key in seen or key not in current:
                continue
            seen.add(key)
            d["score"], d["passed"], d["detail"] = current[key]
            if "trace" in d:
                d["trace_json"] = json.dumps(d.pop("trace"), ensure_ascii=False)
            else:
                d["trace_json"] = ""
            out.append(d)
    out.sort(key=lambda d: (d["model"], d["task_id"], d["idx"]))
    return out


# ------------------------------------------------------------------ cards

def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(lines)


def fmt_cost(row: dict) -> str:
    if row["model"] in SUBSCRIPTION_ONLY:
        return "subscription"
    return f"${row['total_cost_usd']:.4f}"


def fmt_cpc(row: dict) -> str:
    if row["model"] in SUBSCRIPTION_ONLY:
        return "n/a"
    return f"${row['cost_per_correct_usd']:.6f}"


def fmt_verdict(row: dict, anchor_label: str) -> str:
    v = row["verdict_vs_anchor"]
    if v == "reference":
        return "reference"
    p = row["sign_test_p_vs_anchor"]
    return f"{v} (p={p:.3f})"


def overall_md(table: list[dict], anchor_label: str) -> str:
    rows = [[r["rank"], r["label"], f"{r['score']:.3f}",
             f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]", r["tasks"], fmt_cost(r),
             fmt_cpc(r), fmt_verdict(r, anchor_label)] for r in table]
    return md_table(["#", "model", "score", "95% CI", "tasks", "total cost",
                     "cost per correct", f"vs {anchor_label}"], rows)


def tracks_md(tracks: list[dict], present: list[str]) -> str:
    rows = [[t["label"]] + [("" if t[tr] is None else f"{t[tr]:.3f}") for tr in present]
            for t in tracks]
    return md_table(["model"] + present, rows)


def dataset_card(ctx: dict) -> str:
    A, B = ctx["A"], ctx["B"]
    a_top, a_ref = A[0], next(r for r in A if r["model"] == "claude-opus-4-8")
    ratio = a_ref["cost_per_correct_usd"] / a_top["cost_per_correct_usd"]
    n_tasks, n_scores, n_tx = ctx["n_tasks"], ctx["n_scores"], ctx["n_transcripts"]
    tracks_a = [tr for tr in TRACKS if any(t[tr] is not None for t in ctx["TA"])]
    tracks_b = [tr for tr in TRACKS if any(t[tr] is not None for t in ctx["TB"])]
    fable = next(r for r in B if r["model"] == "claude-fable-5-1")
    return f"""---
license: cc-by-4.0
language:
  - en
  - bn
pretty_name: econ-eval
tags:
  - economics
  - benchmark
  - llm-evaluation
  - leaderboard
  - international-trade
  - bangla
  - policy
task_categories:
  - question-answering
  - text-generation
size_categories:
  - 1K<n<10K
configs:
  - config_name: scores
    data_files: scores.csv
    default: true
  - config_name: tasks
    data_files: tasks.jsonl
  - config_name: transcripts
    data_files: transcripts.jsonl
  - config_name: leaderboard_20task
    data_files: leaderboard_20task.csv
  - config_name: leaderboard_50task
    data_files: leaderboard_50task.csv
  - config_name: tracks_20task
    data_files: tracks_20task.csv
  - config_name: tracks_50task
    data_files: tracks_50task.csv
---

# econ-eval: how much do you give up by using a cheap model for an economist's work?

A reproducible benchmark of frontier and cheap LLMs on the work a trade and
policy economist actually does: Balassa RCA from raw BACI values, CAGR and
share arithmetic, bank capital and systemic-risk formulas, small trade-data
pipeline functions, checking a colleague's numbers, and policy writing in
English and Bangla. Every task carries a `source` field, every reference value
is derived from primary data or a stated formula, and every score carries a
bootstrap 95% confidence interval.

Interactive leaderboard: [huggingface.co/spaces/{HF_SPACE}](https://huggingface.co/spaces/{HF_SPACE}).
Harness, tasks and raw results: [{GITHUB}]({GITHUB}).

## What is in this dataset

| file | rows | what |
|---|---|---|
| `scores.csv` | {n_scores:,} | one row per graded completion: task, track, model, sample index, score in [0, 1], pass flag, tokens, latency, grader detail, which judge graded it, which task set it belongs to |
| `tasks.jsonl` | {n_tasks} | the task prompts with grader type, reference value, tolerance, rubric, provenance, and the seed files for agent tasks |
| `transcripts.jsonl` | {n_tx:,} | prompt and full model completion for every completion whose transcript survived (see coverage below) |
| `leaderboard_20task.csv`, `tracks_20task.csv` | 12 | the 20-task, single-judge leaderboard and its per-track scores |
| `leaderboard_50task.csv`, `tracks_50task.csv` | 5 | the 50-task run and its per-track scores |
| `plot-{RUN_A_DATE}.png`, `plot-{RUN_B_DATE}.png` | | quality against cost per correct answer, one per run |

## Leaderboard A: 20 tasks, 12 models, one judge

Twenty tasks (five each of quantitative, reasoning, coding, writing), five
samples per task per model, 100 completions per model. Objective tracks are
graded deterministically (numeric tolerance, sandboxed code execution). The
judged tracks were graded by a single judge, Claude Opus 5, in one pass over
all 12 models. Ten models ran on 2026-08-01; DeepSeek V4.1 Flash and Meta Muse
Spark 1.3 were added on {RUN_A_DATE}, same tasks, same judge.

{overall_md(A, "Opus 4.8")}

Score is the mean over tasks of each task's mean over 5 samples. "vs Opus 4.8"
is an exact two-sided binomial sign test on per-task means, alpha 0.05; with
20 tasks it is a coarse instrument, so read "tied" as "not shown worse".

**The headline:** {a_top['label']} outscores Claude Opus 4.8, {a_top['score']:.3f}
to {a_ref['score']:.3f}, at roughly 1/{ratio:.0f} of the cost per correct answer.
The gap does not clear significance (p = {a_top['sign_test_p_vs_anchor']:.3f}).

Per track:

{tracks_md(ctx["TA"], tracks_a)}

Coding and quantitative are saturated at this task count: the ranking comes
from the writing and reasoning tracks. The two Bangla writing tasks and one
RCA task carry most of the discrimination; seven tasks separate nothing.

**Cost caveat.** Opus 4.8 and Muse Spark ran through CLI harnesses whose input
token counts include the whole harness context, so their cost column is
inflated relative to the raw-API models. The GitHub README reports a corrected
Opus figure; the conclusion does not change.

## Leaderboard B: 50 tasks, 5 models ({RUN_B_DATE})

The 20 tasks above plus 30 "daily work" tasks (bilateral trade shares, RMG
share change, tariff-weighted averages, SRISK, Eisenberg-Noe clearing, CET1,
term premium, HS-code normalisation, referee comments, an agent brief, an
X post, a recruiter reply, plain-Bangla remittance explainer, and more), five
samples each. Five models, all frontier-tier, mostly through subscription CLIs.

{overall_md(B, "GPT-6 Astra")}

Per track:

{tracks_md(ctx["TB"], tracks_b)}

**Read this run with three caveats, all visible in `scores.csv`.**

1. **Mixed judges.** The judge for this run was GPT-6 Astra, which is also a
   contestant. DeepSeek V4.1 Flash and Muse Spark keep their Opus-5-judged
   rows from Leaderboard A for the 20 original tasks (the runner fills only
   missing rows), so their judged scores mix two judges. The `judge` column
   says which judge graded each row.
2. **Incomplete Fable row.** Claude Fable 5.1 covers {fable['tasks']} of 50 tasks
   ({fable['completions']} completions); the run hit the CLI credit wall. Its
   sign test uses only the tasks it completed.
3. **No price for two models.** GPT-6 Astra and Gemini 3.8 Flash are served
   only through subscriptions, so their cost is shown as "subscription", not
   zero.

This table scores the 50 shared tasks only. The four agent-track pilot tasks
in `tasks.jsonl` were run by two models on one task and are excluded here;
the GitHub report of {RUN_B_DATE} includes that task, which is why it shows
DeepSeek at 0.961 rather than 0.960.

## Transcript coverage

`transcripts.jsonl` holds {n_tx:,} of the {n_scores:,} graded completions: all
five Leaderboard B models plus the June 2026 Opus 4.8 and GLM 5.2 runs. The
2026-08-01 OpenRouter fleet (eight models) was run on a machine whose
transcripts were never backed up, so only their scores survive. The `score`,
`passed` and `detail` fields are copied from `scores.csv` at export time, so
they reflect the current judge, not the judge at run time (the June 2026 rows
were regraded by Opus 5 on 2026-08-01). Rows with a tool trace (agent track)
carry it as `trace_json`.

## Method, briefly

- **Graders.** `numeric`: parse the `ANSWER:` line, compare to the reference
  within a per-task relative tolerance (0.5 percent for RCA). `code_exec`: run
  the returned code in a sandbox against assertions. `judge`: a rubric of 4 to
  5 points scored 0 or 1 each, blind to model identity, absolute not
  comparative. `artifact`: numeric-on-file for the agent pilot.
- **Statistics.** Percentile bootstrap over tasks then samples, 5,000
  iterations, seed 0. Head-to-head: exact two-sided binomial sign test on
  per-task means, ties dropped. Pure numpy.
- **References.** BACI 2013, 2022, 2023 (CEPII, Etalab 2.0 licence; Gaulier
  and Zignago 2010) and WTO applied MFN lines via the TradeWeave parquet tree;
  NY Fed ACM term-structure series; Brownlees-Engle SRISK, Eisenberg-Noe,
  Basel III and Fisher formulas on author-defined inputs. No fabricated values.
- **Task files are append-only.** Editing a prompt would invalidate every
  cached completion for it.

## Licence and use

Tasks, rubrics, scores and this card: CC BY 4.0. Model completions in
`transcripts.jsonl` are reproduced as evaluation records; the terms of each
provider apply to any other use of their outputs. Trade figures embedded in
prompts derive from BACI (CEPII) under Etalab 2.0.

## Citation

```
@misc{{econeval2026,
  author = {{Hossen, Md Deluair}},
  title = {{econ-eval: an economist's benchmark for cheap and frontier LLMs}},
  year = {{2026}},
  url = {{{GITHUB}}}
}}
```

Exported {ctx['today']} by `scripts/export_hf.py` from `results/scores.sqlite`
at commit `{ctx['commit']}`.
"""


def space_card() -> str:
    return f"""---
title: econ-eval leaderboard
emoji: 📈
colorFrom: blue
colorTo: gray
sdk: static
pinned: true
license: cc-by-4.0
short_description: Frontier vs cheap LLMs on an economist's daily work
---

Static leaderboard for the econ-eval benchmark. Data: [{HF_DATASET}](https://huggingface.co/datasets/{HF_DATASET}).
Harness: [{GITHUB}]({GITHUB}). Regenerate with `scripts/export_hf.py` in that repo.
"""


# ------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--transcripts", type=Path, action="append", default=[])
    args = ap.parse_args()
    out_ds = args.out / "dataset"
    out_sp = args.out / "space"
    out_ds.mkdir(parents=True, exist_ok=True)
    out_sp.mkdir(parents=True, exist_ok=True)

    tasks = load_tasks()
    trows = task_rows(tasks)
    with (out_ds / "tasks.jsonl").open("w") as f:
        for r in trows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    srows = score_rows(tasks)
    with (out_ds / "scores.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
        w.writeheader()
        w.writerows(srows)

    orig20 = {r["task_id"] for r in srows if r["task_set"] == "original-20"}
    fifty = {t.id for t in tasks if t.track != "agent"}
    assert len(orig20) == 20 and len(fifty) == 50, (len(orig20), len(fifty))
    A, TA = leaderboard(RUN_A_MODELS, "claude-opus-4-8", orig20)
    B, TB = leaderboard(RUN_B_MODELS, "gpt-6-astra", fifty)
    for name, table in (("leaderboard_20task", A), ("leaderboard_50task", B),
                        ("tracks_20task", TA), ("tracks_50task", TB)):
        with (out_ds / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(table)

    tx_dirs = [ROOT / "results"] + args.transcripts
    current = {(r["model"], r["task_id"], r["idx"]): (r["score"], bool(r["passed"]), r["detail"])
               for r in srows}
    tx = collect_transcripts(tx_dirs, current)
    with (out_ds / "transcripts.jsonl").open("w") as f:
        for r in tx:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    for d in (RUN_A_DATE, RUN_B_DATE):
        shutil.copy(ROOT / "results" / f"plot-{d}.png", out_ds / f"plot-{d}.png")

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unknown"  # exported from a tarball, not a checkout
    ctx = {"A": A, "B": B, "TA": TA, "TB": TB, "n_tasks": len(trows),
           "n_scores": len(srows), "n_transcripts": len(tx),
           "today": datetime.now(UTC).date().isoformat(), "commit": commit}
    (out_ds / "README.md").write_text(dataset_card(ctx))

    data = {"generated": ctx["today"], "commit": commit, "dataset": HF_DATASET,
            "github": GITHUB, "runA": {"date": RUN_A_DATE, "overall": A, "tracks": TA,
                                        "trackNames": [t for t in TRACKS if any(x[t] is not None for x in TA)]},
            "runB": {"date": RUN_B_DATE, "overall": B, "tracks": TB,
                     "trackNames": [t for t in TRACKS if any(x[t] is not None for x in TB)]},
            "nScores": len(srows), "nTasks": len(trows), "nTranscripts": len(tx)}
    template = (ROOT / "scripts" / "hf_space_template.html").read_text()
    (out_sp / "index.html").write_text(
        template.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    (out_sp / "README.md").write_text(space_card())

    print(f"tasks {len(trows)}  scores {len(srows)}  transcripts {len(tx)}")
    for r in A:
        print(f"A {r['rank']:2d} {r['label']:28s} {r['score']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] "
              f"cpc {r['cost_per_correct_usd']:.6f} {r['verdict_vs_anchor']} p={r['sign_test_p_vs_anchor']}")
    for r in B:
        print(f"B {r['rank']:2d} {r['label']:28s} {r['score']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] "
              f"tasks {r['tasks']} {r['verdict_vs_anchor']} p={r['sign_test_p_vs_anchor']}")


if __name__ == "__main__":
    main()
