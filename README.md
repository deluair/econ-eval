# econ-eval

A reproducible benchmark that asks a single question: **on the work an
economist actually does, how much do you give up by using a cheap model?**

Ten models answer the same 20 tasks, five times each (1,000 completions), across
four tracks: quantitative trade/macro computation, economic reasoning, domain
coding, and policy writing. Objective tracks are graded deterministically
(numeric tolerance, sandboxed code execution). Subjective tracks are rubric
graded by a model judge. Every score carries a bootstrap 95% CI, and every
model is compared to Claude Opus 4.8 with an exact binomial sign test.

Run of 2026-07-31/08-01. Objective tracks are complete; the subjective half is
mid-regrade (see [Status](#status)).

## Headline result

On the objective half of the benchmark, **six of the ten models score a perfect
1.000, and the five that are not Opus cost 8x to 539x less per correct answer.**

| model | objective score | 95% CI | total cost | cost per correct |
|---|---|---|---|---|
| claude-opus-4-8 | **1.000** | [1.000, 1.000] | $2.8501 | $0.057003 |
| deepseek/deepseek-v4-flash-0731 | **1.000** | [1.000, 1.000] | $0.0099 | $0.000199 |
| google/gemini-3.6-flash | **1.000** | [1.000, 1.000] | $0.3437 | $0.006873 |
| moonshotai/kimi-k3 | **1.000** | [1.000, 1.000] | $0.3494 | $0.006988 |
| openai/gpt-5.6-luna | **1.000** | [1.000, 1.000] | $0.0053 | $0.000106 |
| x-ai/grok-4.5 | **1.000** | [1.000, 1.000] | $0.1255 | $0.002509 |
| nvidia/nemotron-3-ultra-550b-a55b | 0.980 | [0.920, 1.000] | $0.1056 | $0.002154 |
| meta-llama/llama-4-maverick | 0.960 | [0.860, 1.000] | $0.0059 | $0.000122 |
| minimax/minimax-m3 | 0.960 | [0.880, 1.000] | $0.0558 | $0.001163 |
| glm-5.2 | 0.900 | [0.700, 1.000] | $0.0056 | $0.000124 |

Score is the mean over tasks of each task's mean over 5 samples, on the 10
objective tasks (500 graded completions). Cost covers those completions only.
No model beats or loses to Opus at p < 0.05 on this half: the sign test returns
p >= 0.5 for all nine challengers, because the objective tasks are saturated.
**Read that as "these tasks no longer discriminate at the top", not as
"the models are equal".** See [Task difficulty](#task-difficulty-is-the-binding-constraint).

The cost column is not like for like. Opus is called through the `claude` CLI,
so its `input_tokens` include the entire Claude Code harness context: 10,335
tokens per call, against 88 to 291 for the raw API models. Substituting the
median API prompt size (114 tokens) and keeping Opus's real output tokens puts
Opus at **$0.2948 total, $0.005897 per correct**, still 56x the cheapest perfect
scorer. Both figures are reported so neither flatters the conclusion.

## Latency and verbosity

Cost is not the only axis on which the perfect scorers differ. Mean wall-clock
latency per call and mean output tokens per call, objective tasks only:

| model | mean latency (s) | output tokens per call |
|---|---|---|
| moonshotai/kimi-k3 | 14.4 | 432 |
| minimax/minimax-m3 | 11.8 | 869 |
| deepseek/deepseek-v4-flash-0731 | 9.0 | 650 |
| claude-opus-4-8 | 6.9 | 213 |
| x-ai/grok-4.5 | 4.7 | 321 |
| google/gemini-3.6-flash | 4.6 | 897 |
| meta-llama/llama-4-maverick | 4.5 | 123 |
| nvidia/nemotron-3-ultra-550b-a55b | 4.0 | 567 |
| openai/gpt-5.6-luna | 3.6 | 161 |
| glm-5.2 | 2.8 | 24 |

Among the five non-Opus perfect scorers, `gpt-5.6-luna` wins on every axis at
once: tied top score, cheapest per correct answer, and fastest. `kimi-k3` gets
the same score for 66x the cost and 4x the latency. Verbosity drives the cost
spread more than headline price does: `gemini-3.6-flash` emits 897 output
tokens per call against Luna's 161, which is most of why it lands 65x higher
per correct answer despite being only 12x more expensive per token.

Latencies were measured with up to ten evals running in parallel, so treat them
as relative, not as clean single-stream benchmarks.

## Where the cheap models actually break

Four models dropped points, and the failures are three distinct kinds. This is
the useful signal, not the leaderboard.

| model | task | fails | grader detail | kind of failure |
|---|---|---|---|---|
| glm-5.2 | quant-rca-6109 | 5/5 | got 6.58, ref 65.36 | order-of-magnitude slip |
| meta-llama/llama-4-maverick | quant-rca-6109 | 2/5 | got 64.09, ref 65.36 | precision, 1.94% off a 0.5% tolerance |
| minimax/minimax-m3 | quant-rca-6109 | 1/5 | no number found | format, no parsable answer |
| nvidia/nemotron-3-ultra-550b-a55b | quant-rca-6109 | 1/5 | no number found | format, no parsable answer |
| minimax/minimax-m3 | code-cagr | 1/5 | `NameError: name 'cagr' is not defined` | code, function never defined |

`quant-rca-6109` accounts for nine of the ten objective failures. It asks for a
Balassa RCA from four raw trade values, a two-ratio calculation with no
intermediate scaffolding:

> RCA = (9,288,364.183 / 65,871,533.413) / (52,091,992.664 / 24,145,991,347.414) = 65.36

GLM 5.2 returns 6.58 on all five samples, low by a factor of 9.93. It is not
noise: the model reliably drops a decade somewhere in the nested division while
producing confident, well-formatted output. That is the failure mode that
matters for economics work, because nothing downstream flags it. This
reproduces a finding from the earlier two-model run (commit 52c09a7, "GLM fails
inline RCA 0/5").

Llama's 64.09 is a different animal: arithmetically close, and it would pass a
2% tolerance. Whether that counts as a failure is a policy choice this
benchmark makes explicit (0.5%), not a fact about the model.

## Models

Nine contestants plus Opus. Prices are USD per 1M tokens, read from the
OpenRouter catalog API on 2026-07-31 and stored in `econ_eval/config.py`.

| adapter | model id | access path | $/M in | $/M out |
|---|---|---|---|---|
| opus | `claude-opus-4-8` | `claude` CLI, subscription | 5.00 | 25.00 |
| glm | `glm-5.2` | z.ai direct, Anthropic-compatible | 0.60 | 2.20 |
| gemini-flash | `google/gemini-3.6-flash` | OpenRouter | 1.50 | 7.50 |
| deepseek-0731 | `deepseek/deepseek-v4-flash-0731` | OpenRouter | 0.14 | 0.28 |
| kimi-k3 | `moonshotai/kimi-k3` | OpenRouter | 3.00 | 15.00 |
| nemotron-ultra | `nvidia/nemotron-3-ultra-550b-a55b` | OpenRouter | 0.60 | 3.60 |
| minimax-m3 | `minimax/minimax-m3` | OpenRouter | 0.30 | 1.20 |
| luna | `openai/gpt-5.6-luna` | OpenRouter | 0.10 | 0.60 |
| grok | `x-ai/grok-4.5` | OpenRouter | 2.00 | 6.00 |
| llama | `meta-llama/llama-4-maverick` | OpenRouter | 0.20 | 0.80 |

Two notes on selection. `kimi-k3` at $3.00/$15.00 is not a cheap model and is
included only because it was requested by name. `meta-llama/llama-4-maverick`
is the newest Meta model in the catalog; there is no Llama 5.

## Task suite

Twenty tasks, five per track, 5 samples each. Every task carries a `source`
field and the loader refuses to construct one without it.

| track | tasks | grader | how it is scored |
|---|---|---|---|
| quantitative | 5 | `numeric` | parse the `ANSWER:` line, compare to a reference within a per-task relative tolerance (0.5% for RCA) |
| coding | 5 | `code_exec` | execute the returned code in a sandbox against assertions |
| reasoning | 5 | `judge` | model judge scores each rubric point 0 or 1 |
| writing | 5 | `judge` | same, including two Bangla-language tasks |

```
quant-cotton-share      quant-hs6109-sum     quant-rca-6109
quant-trade-balance     quant-unit-trap
code-aggregate          code-cagr            code-hhi
code-method-of-reflections                   code-rca
reason-export-diversification                reason-ldc-graduation
reason-passthrough-netting                   reason-rca-interpretation
reason-taka-depreciation
write-bangla-formal     write-exec-summary   write-oped-bangla
write-policy-brief      write-tight-constraints
```

Reference values are computed by `scripts/build_references.py` from primary
data (BACI via the TradeWeave parquet tree, IMF, FRED) and verified before
commit. No fabricated values. The RCA reference above was re-derived from its
four inputs during this run and matched to 4 decimal places.

Task files are effectively append-only: editing a prompt invalidates every
cached completion for it. Add tasks, do not rewrite them.

## Grading

**Objective tracks** need no judge. `numeric` extracts the answer and applies a
relative tolerance; a missing or unparsable number scores 0, which is why
"no number found" appears as a failure mode. `code_exec` runs the model's code
against assertions and scores 0 on any exception.

**Subjective tracks** are rubric graded: the judge sees the task, the answer,
and a numbered rubric, and returns a JSON map of rubric index to 0 or 1. The
score is the fraction of rubric points hit; pass is >= 0.5. The judge never
sees which model produced an answer, and rubric grading is absolute rather than
comparative, so there is no position bias to cancel. A pairwise, order-swapped
comparator exists in `econ_eval/graders/judge.py` for A/B use.

The judge is **Claude Fable 5**, called through the same `claude` CLI as the
Opus contestant. It replaced DeepSeek V4 Flash on 2026-07-31. One caveat stated
plainly: an Anthropic model judging an Anthropic contestant is not a neutral
third party, and the Opus subjective scores should be read with that in mind.
All subjective rows are graded by a single judge or the comparison is void,
which is exactly what the current regrade enforces.

## Statistics

- **Point score**: mean over tasks of each task's mean over its 5 samples, so a
  task with more samples cannot dominate.
- **95% CI**: percentile bootstrap, 5,000 iterations, seed 0. Resamples tasks
  with replacement, and within each resampled task resamples its samples. This
  is a task-level CI, so it widens when models disagree across tasks rather
  than across repeats of one task.
- **Head to head**: exact two-sided binomial sign test on per-task mean
  differences, ties dropped, alpha = 0.05. The harness refuses to name a winner
  above that threshold. With 10 objective tasks and near-ceiling scores, no
  comparison clears it, and the report says so rather than implying a ranking.

Pure numpy, no scipy. Deterministic given the seed.

## Status

| half | rows | state |
|---|---|---|
| objective (quantitative, coding) | 500 | complete, reported above |
| subjective (reasoning, writing) | 500 | **not reportable yet**: 198 rows regraded by Fable, 302 still carry DeepSeek scores |

All 1,000 completions are generated and cached; no model needs to be called
again. The regrade stalled because the Claude subscription ran out of usage
credits mid-pass (HTTP 429, `out_of_credits`), and the judge runs through that
same CLI. Mixed-judge scores are not comparable across models, so the
subjective tracks are withheld rather than published with a footnote.

To finish once credits are available:

```bash
uv run python scripts/regrade_judge.py \
  ../../../results/transcripts-2026-06-22.jsonl results/transcripts-2026-07-31-*.jsonl
uv run python -m econ_eval --date <date> report
```

The script is resumable: it skips rows already marked `fable-judge` in
`scores.detail` and regrades only the remaining 302.

## Setup

```bash
make setup                      # uv sync
export OPENROUTER_API_KEY=...   # the 8-model fleet (OPENAI_API_KEY also accepted)
export ZAI_API_KEY=...          # GLM 5.2 direct
# Opus and the Fable judge run through the `claude` CLI under your Claude Code
# login, no API key needed.
```

## Use

```bash
make probe    # confirm every contestant and the judge are reachable
make dry      # print task and call counts, no model calls
make eval     # all tasks x all models x N=5, graded and cached
make report   # results/report-<date>.md plus the quality-vs-cost plot
make test     # 47 unit tests, no live calls

# one model at a time, which is how the fleet was actually run
uv run python -m econ_eval --date <date> eval -n 5 --models grok
# report a subset of tracks
uv run python -m econ_eval --date <date> report --tracks quantitative,coding
```

The runner is resumable and keyed on (task, model, sample index): rerunning
fills only what is missing. Scored rows go to `results/scores.sqlite` (tracked
in git), transcripts to `results/transcripts-*.jsonl` (gitignored, backed up to
Google Drive by `backup.sh`).

Running one process per model in parallel is safe; SQLite is opened with
`busy_timeout=60000`. The `claude` CLI is the exception, it exits non-zero under
concurrency, so the judge adapter retries three times with backoff and the
regrade script runs at 3 workers.

## Task difficulty is the binding constraint

Six models at exactly 1.000 is a statement about the benchmark, not about the
models. These tasks were built to be verifiable against primary data, and
verifiable turned out to correlate with easy: compute-over-provided-inputs and
deterministic coding are close to solved at every price point tested.

The one task that separates the field, `quant-rca-6109`, does it by removing
scaffolding rather than by adding difficulty. It hands over four raw numbers
and a formula and asks for one nested division. That is what caught GLM's
factor-of-10 error and Llama's precision drift.

The next tasks worth adding follow that pattern: multi-step chains where an
early unit error propagates, netting and aggregation traps, questions whose
correct answer is "the data does not support this", and reasoning that has to
survive a hostile reading. Until then, treat the objective half as a floor test
that most current models pass, and expect the discrimination to come from the
subjective tracks.

## Adding tasks

One YAML per task in `tasks/`. Required: `id`, `track`, `prompt`, `grader`,
`source`. The loader validates track and grader type and rejects a task with no
source. Quantitative references come from `scripts/build_references.py` against
primary data, never from a model and never from memory. See
`docs/CODEBASE_LEDGER.md` for conventions and known quirks, and
`docs/superpowers/specs/` for the original design.
