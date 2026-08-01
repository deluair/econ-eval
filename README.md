# econ-eval

A reproducible benchmark that asks a single question: **on the work an
economist actually does, how much do you give up by using a cheap model?**

Ten models answer the same 20 tasks, five times each (1,000 completions), across
four tracks: quantitative trade/macro computation, economic reasoning, domain
coding, and policy writing. Objective tracks are graded deterministically
(numeric tolerance, sandboxed code execution). Subjective tracks are rubric
graded by Claude Opus 5. Every score carries a bootstrap 95% CI, and every
challenger is compared to Claude Opus 4.8 with an exact binomial sign test.

Run completed 2026-08-01. All 1,000 completions graded, all 500 subjective rows
scored by a single judge.

## Leaderboard

| # | model | score | 95% CI | total cost | cost per correct | vs Opus |
|---|---|---|---|---|---|---|
| 1 | claude-opus-4-8 | 0.979 | [0.951, 0.997] | $7.8015 | $0.078015 | reference |
| 2 | moonshotai/kimi-k3 | 0.975 | [0.949, 0.996] | $2.5008 | $0.025008 | tied (p=1.000) |
| 3 | google/gemini-3.6-flash | 0.956 | [0.918, 0.988] | $1.1091 | $0.011091 | tied (p=0.125) |
| 4 | openai/gpt-5.6-luna | 0.947 | [0.905, 0.984] | $0.0257 | $0.000257 | tied (p=0.125) |
| 5 | x-ai/grok-4.5 | 0.940 | [0.895, 0.980] | $0.4953 | $0.004953 | loses (p=0.016) |
| 6 | deepseek/deepseek-v4-flash-0731 | 0.934 | [0.889, 0.975] | $0.0332 | $0.000332 | loses (p=0.008) |
| 7 | minimax/minimax-m3 | 0.922 | [0.866, 0.969] | $0.1974 | $0.002035 | loses (p=0.004) |
| 8 | nvidia/nemotron-3-ultra-550b-a55b | 0.899 | [0.809, 0.973] | $0.2210 | $0.002377 | loses (p=0.031) |
| 9 | glm-5.2 | 0.873 | [0.761, 0.949] | $0.0388 | $0.000408 | loses (p=0.002) |
| 10 | meta-llama/llama-4-maverick | 0.864 | [0.783, 0.934] | $0.0139 | $0.000143 | loses (p=0.002) |

Score is the mean over 20 tasks of each task's mean over 5 samples. Cost covers
all 100 completions per model. "vs Opus" is an exact two-sided sign test on
per-task means, alpha = 0.05.

**The headline: `gpt-5.6-luna` is statistically indistinguishable from Opus 4.8
at 1/304th the cost per correct answer.** It scores 0.947 against Opus's 0.979,
and with 20 tasks that gap does not clear significance (p = 0.125). Three models
survive the comparison: Kimi K3, Gemini 3.6 Flash, and Luna. Six do not.

The cost column is not like for like, and correcting it does not change the
conclusion. Opus runs through the `claude` CLI, so its `input_tokens` carry the
entire Claude Code harness context: 8,287 tokens per call against a 101-token
median for the raw API models. Substituting that median and keeping Opus's real
output tokens gives **$3.7088 total, $0.037088 per correct**, still 144x Luna.
Both figures are reported so neither flatters the result.

## Which track separates the models

Not all four tracks carry information. Spread between best and worst model:

| track | best | worst | spread | verdict |
|---|---|---|---|---|
| coding | 1.000 | 0.960 | 0.040 | saturated, near-useless for ranking |
| reasoning | 1.000 | 0.828 | 0.172 | mild separation |
| quantitative | 1.000 | 0.800 | 0.200 | separation from one task |
| writing | 0.914 | 0.638 | 0.276 | **the discriminating track** |

Nine of ten models score a perfect 1.000 on coding, and six do on
quantitative. If this benchmark were objective-only it would report a ten-way
tie and no significant differences anywhere, which is exactly what it reported
before the subjective tracks were graded. **The ranking above exists because of
the writing and reasoning tracks.**

### Per-track detail

| model | quantitative | reasoning | coding | writing |
|---|---|---|---|---|
| claude-opus-4-8 | 1.000 | 1.000 | 1.000 | **0.914** |
| moonshotai/kimi-k3 | 1.000 | 1.000 | 1.000 | 0.900 |
| google/gemini-3.6-flash | 1.000 | 0.970 | 1.000 | 0.852 |
| openai/gpt-5.6-luna | 1.000 | 0.926 | 1.000 | 0.862 |
| x-ai/grok-4.5 | 1.000 | 0.934 | 1.000 | 0.826 |
| deepseek/deepseek-v4-flash-0731 | 1.000 | 0.932 | 1.000 | 0.806 |
| minimax/minimax-m3 | 0.960 | 0.892 | 0.960 | 0.876 |
| nvidia/nemotron-3-ultra-550b-a55b | 0.960 | 1.000 | 1.000 | **0.638** |
| glm-5.2 | 0.800 | 0.872 | 1.000 | 0.820 |
| meta-llama/llama-4-maverick | 0.920 | 0.828 | 1.000 | 0.708 |

## Three failure modes worth knowing

### 1. Bangla is where the cheap models actually fall over

Nemotron 3 Ultra scores a perfect 1.000 on reasoning and coding, then collapses
to 0.638 on writing. The collapse is entirely linguistic: 0.75 to 0.84 on the
three English writing tasks, 0.40 on both Bangla ones. Mean score across the two
Bangla tasks:

| model | Bangla |
|---|---|
| claude-opus-4-8 | 0.955 |
| openai/gpt-5.6-luna | 0.920 |
| moonshotai/kimi-k3 | 0.895 |
| google/gemini-3.6-flash | 0.895 |
| minimax/minimax-m3 | 0.885 |
| deepseek/deepseek-v4-flash-0731 | 0.870 |
| x-ai/grok-4.5 | 0.855 |
| glm-5.2 | 0.805 |
| meta-llama/llama-4-maverick | 0.685 |
| nvidia/nemotron-3-ultra-550b-a55b | 0.400 |

Nemotron does emit Bangla script, so this is not a refusal or an
encoding failure. It emits *worse* Bangla: 71% Bangla characters against a
consistent 85% for everyone else, the rest being transliterated English where a
Bangla term exists, which the rubric explicitly penalises. Its five samples
score 0.4, 0.2, 0.4, 0.4, 0.6, so the weakness is consistent rather than noise.
For Bangla-language policy work, the cheap tier is not interchangeable and the
English scores will not warn you.

### 2. A confident order-of-magnitude error

Nine of the ten objective failures land on one task, `quant-rca-6109`, which
asks for a Balassa RCA from four raw trade values with no intermediate
scaffolding:

> RCA = (9,288,364.183 / 65,871,533.413) / (52,091,992.664 / 24,145,991,347.414) = 65.36

| model | task | fails | detail | kind |
|---|---|---|---|---|
| glm-5.2 | quant-rca-6109 | 5/5 | got 6.58, ref 65.36 | order-of-magnitude slip |
| meta-llama/llama-4-maverick | quant-rca-6109 | 2/5 | got 64.09 | precision, 1.94% against a 0.5% tolerance |
| minimax/minimax-m3 | quant-rca-6109 | 1/5 | no number found | format |
| nvidia/nemotron-3-ultra | quant-rca-6109 | 1/5 | no number found | format |
| minimax/minimax-m3 | code-cagr | 1/5 | `NameError: name 'cagr' is not defined` | code |

GLM 5.2 returns 6.58 on all five samples, low by a factor of 9.93, while
producing confident well-formatted output. That is the failure mode that
matters for economics work: nothing downstream flags it. This reproduces a
finding from the earlier two-model run (commit 52c09a7). Llama's 64.09 is a
different animal, arithmetically close and passing at a 2% tolerance; whether
it counts as a failure is a policy choice this benchmark makes explicit.

### 3. Verbosity, not headline price, drives cost

| model | mean latency (s) | output tokens per call |
|---|---|---|
| moonshotai/kimi-k3 | 48.7 | 1,635 |
| claude-opus-4-8 | 22.5 | 1,463 |
| deepseek/deepseek-v4-flash-0731 | 19.5 | 1,126 |
| minimax/minimax-m3 | 17.7 | 1,586 |
| x-ai/grok-4.5 | 12.5 | 731 |
| google/gemini-3.6-flash | 7.4 | 1,462 |
| openai/gpt-5.6-luna | 5.4 | 414 |
| glm-5.2 | 5.4 | 153 |
| nvidia/nemotron-3-ultra-550b-a55b | 4.8 | 597 |
| meta-llama/llama-4-maverick | 4.8 | 152 |

Gemini 3.6 Flash costs 43x more per correct answer than Luna while being only
12.5x more expensive per output token. The remainder is verbosity: 1,462 output
tokens per call against Luna's 414. Kimi K3 buys its statistical tie with Opus
at 3.1x less cost, but at 9x Luna's latency and the slowest wall clock in the
field. GLM 5.2 and Llama 4 Maverick are the terse ones at ~150 tokens per call,
which is most of why they are the cheapest per correct answer despite ranking
9th and 10th on quality.

Latencies were measured with up to ten evals running in parallel, so treat them
as relative rather than clean single-stream numbers.

## Models

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

Prices are USD per 1M tokens, read from the OpenRouter catalog API on
2026-07-31 and stored in `econ_eval/config.py`. Two notes on selection:
`kimi-k3` at $3.00/$15.00 is not a cheap model and is included only because it
was requested by name, and `llama-4-maverick` is the newest Meta model in the
catalog, since there is no Llama 5.

## Task suite

Twenty tasks, five per track, 5 samples each. Every task carries a `source`
field and the loader refuses to construct one without it.

| track | grader | how it is scored |
|---|---|---|
| quantitative | `numeric` | parse the `ANSWER:` line, compare to a reference within a per-task relative tolerance (0.5% for RCA) |
| coding | `code_exec` | execute the returned code in a sandbox against assertions |
| reasoning | `judge` | model judge scores each rubric point 0 or 1 |
| writing | `judge` | same, including two Bangla-language tasks |

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
commit. No fabricated values. The RCA reference was re-derived from its four
inputs during this run and matched to four decimal places.

Task files are effectively append-only: editing a prompt invalidates every
cached completion for it. Add tasks, do not rewrite them.

## Grading

**Objective tracks** need no judge. `numeric` extracts the answer and applies a
relative tolerance; a missing or unparsable number scores 0, which is why "no
number found" appears as a failure mode. `code_exec` runs the model's code
against assertions and scores 0 on any exception.

**Subjective tracks** are rubric graded: the judge sees the task, the answer,
and a numbered rubric, and returns a JSON map of rubric index to 0 or 1. Score
is the fraction of rubric points hit; pass is >= 0.5. The judge never sees which
model produced an answer, and rubric grading is absolute rather than
comparative, so there is no position bias to cancel. A pairwise, order-swapped
comparator exists in `econ_eval/graders/judge.py` for A/B use. A representative
rubric, from `write-bangla-formal`:

```
0  Written in fluent, grammatically correct Bangla
1  Formal administrative / policy-memo register (not casual, not op-ed)
2  Uses correct Bangla economic terms rather than transliterated English
3  Recommends one concrete, specific diversification step
4  Coherent and within 90 to 120 words
```

The judge is **Claude Opus 5** (`claude-opus-5`), called through the same
`claude` CLI as the Opus 4.8 contestant. Two caveats stated plainly:

1. **The judge is not neutral.** Opus 5 grading Opus 4.8 is same-family
   refereeing, and Opus 4.8's subjective scores should be read with that in
   mind. Its top-line lead comes from the writing track, which is judged. The
   objective tracks are immune, being deterministically graded, and there Opus
   ties five other models exactly.
2. **All 500 subjective rows are graded by one judge.** Judges are not
   interchangeable, so mixing them would void cross-model comparison. When the
   judge changed, every row was regraded, not just the ungraded ones.
   `DONE_PREFIX` in `scripts/regrade_judge.py` enforces this: changing judges
   means changing that string, which invalidates every existing grade.

## Statistics

- **Point score**: mean over tasks of each task's mean over its 5 samples, so a
  task with more samples cannot dominate.
- **95% CI**: percentile bootstrap, 5,000 iterations, seed 0. Resamples tasks
  with replacement, and within each resampled task resamples its samples. This
  is a task-level CI, so it widens when models disagree across tasks rather
  than across repeats of one task.
- **Head to head**: exact two-sided binomial sign test on per-task mean
  differences, ties dropped, alpha = 0.05. The harness refuses to name a winner
  above that threshold, which is why three models are reported as tied with
  Opus rather than ranked below it.

Pure numpy, no scipy. Deterministic given the seed.

With 20 tasks, the sign test needs a challenger to lose 7 or more decided tasks
without winning any to reach p < 0.05. That is a coarse instrument: it cannot
distinguish "as good as Opus" from "not yet proven worse". Read the three ties
as the latter.

## Setup

```bash
make setup                      # uv sync
export OPENROUTER_API_KEY=...   # the 8-model fleet (OPENAI_API_KEY also accepted)
export ZAI_API_KEY=...          # GLM 5.2 direct
# Opus and the Opus 5 judge run through the `claude` CLI under your Claude Code
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
# regrade every judge row after changing judges (16 workers by default)
REGRADE_WORKERS=16 uv run python scripts/regrade_judge.py results/transcripts-*.jsonl
```

The runner is resumable and keyed on (task, model, sample index): rerunning
fills only what is missing. Scored rows go to `results/scores.sqlite` (tracked
in git), transcripts to `results/transcripts-*.jsonl` (gitignored, backed up to
Google Drive by `backup.sh`).

Running one process per model in parallel is safe; SQLite is opened with
`busy_timeout=60000`. Sixteen concurrent `claude` CLI calls are also fine:
measured by wall clock, the judge regrade ran 402 rows in 208s at 16 workers
(116 rows/min) against 98 rows in 231s at 3 workers (25.5 rows/min). That is
4.6x for 5.3x the workers, so scaling is sublinear and per-call CLI startup
dominates. Note that the CLI reports credit exhaustion as either exit 1 with
empty stderr or exit 0 with an `api_error` envelope, and the first form is easy
to misread as a concurrency fault. The tell is that a credit wall fails every
retry instantly with zero rows completed.

## What this benchmark cannot yet tell you

Coding is saturated and quantitative is close, so most of the ranking rests on
two judged tracks and a single arithmetic task. Concretely:

- **The objective tasks are too easy.** They were built to be verifiable
  against primary data, and verifiable correlated with easy. The one task that
  separates the field does it by removing scaffolding, not by adding
  difficulty.
- **The judged tracks carry the ranking, and the judge is related to one
  contestant.** A neutral judge with sufficient quota would strengthen every
  subjective conclusion here.
- **20 tasks is a coarse sign test.** Three ties with Opus mean "not proven
  worse", not "proven equal".

The next tasks worth adding follow the RCA pattern: multi-step chains where an
early unit error propagates, netting and aggregation traps, questions whose
correct answer is "the data does not support this", and more Bangla work, since
that is where the spread is widest and where the English scores are actively
misleading.

## Adding tasks

One YAML per task in `tasks/`. Required: `id`, `track`, `prompt`, `grader`,
`source`. The loader validates track and grader type and rejects a task with no
source. Quantitative references come from `scripts/build_references.py` against
primary data, never from a model and never from memory. See
`docs/CODEBASE_LEDGER.md` for conventions and known quirks, and
`docs/superpowers/specs/` for the original design.
