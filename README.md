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
