# econ-eval

A reproducible benchmark comparing **Claude Opus 4.8** and **GLM 5.2** (z.ai) on
the work an economist actually does: quantitative trade/macro questions,
economic reasoning, domain coding, and policy writing. Subjective tracks are
graded by a neutral third judge (**DeepSeek V4**), blind and order-swapped to
cancel position bias. Results carry bootstrap 95% CIs and a paired sign test.

## Setup

```bash
make setup           # uv sync
export ZAI_API_KEY=...        # GLM (already set on this machine)
export DEEPSEEK_API_KEY=...   # judge
# Opus runs via the `claude` CLI under your Claude Code login - no API key.
```

## Use

```bash
make probe           # confirm opus, glm-5.2, and the judge are reachable
make dry             # print task/call counts, no model calls
make eval            # run all tasks x both models x N=5, grade, cache
make report          # build results/report-<date>.md + plot
make test            # unit tests (no live calls)
```

The runner is resumable: re-running re-grades from cache and only fills missing
samples. Transcripts go to `results/transcripts-*.jsonl`; scored rows to
`results/scores.sqlite`.

## Adding tasks

One YAML per task in `tasks/`. Every task needs a real `source`. Quantitative
reference values are computed by `scripts/build_references.py` from primary
data (BACI / IMF / FRED / TradeWeave parquet) and verified before commit. No
fabricated values. See `docs/superpowers/specs/` for the full design.

## Cost caveat (important)

Opus is called through the `claude` CLI, so each call's reported `input_tokens`
includes the entire Claude Code harness context (tools, skills, memory) - on
the order of 10k+ tokens per call regardless of prompt size. GLM is a bare API
call. The cost-per-correct figure for Opus is therefore an upper bound and is
NOT directly comparable to GLM's. Treat the cost column as "Opus via this
subscription path" vs "GLM via raw API", not a like-for-like token cost.

## Interpreting results

The harness will not declare a winner unless the paired sign test is
significant at alpha=0.05. With a small task set or low N you will often see
"no significant difference" even at a 1.00 win-rate - that is correct, not a
bug. Scale up N (`-n`) and add tasks for a real verdict. The seed tasks are
deliberately tractable (compute-over-provided-data, deterministic coding); add
harder, more discriminating tasks to widen the gap.
