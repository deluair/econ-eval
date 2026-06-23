# econ-eval — Opus 4.8 vs GLM 5.2 benchmark in economics/trade/policy

Design spec. Status: approved shape, pending spec review.
Date: 2026-06-22. Author: Md Deluair Hossen.

## 1. Goal

A reproducible benchmark that measures whether Claude Opus 4.8 or GLM 5.2
(z.ai) is better at the work this user actually does: economic and trade
reasoning, quantitative correctness on real data, domain coding, and policy
writing. Results carry confidence intervals and a paired significance test, not
single-run anecdotes. The harness is general; the initial task set is small.

Non-goals: a public leaderboard, a web UI, support for arbitrary providers
beyond the two contestants, or fine-tuning. Those are out of scope.

## 2. Models under test

| Role | Model | How it is called | Auth |
|---|---|---|---|
| Contestant A | Claude Opus 4.8 (claude-opus-4-8) | claude CLI headless: claude -p <prompt> --output-format json | Claude Code subscription (already logged in) |
| Contestant B | GLM 5.2 (glm-5.2) | anthropic SDK, base_url=https://api.z.ai/api/anthropic | ZAI_API_KEY (set) |

Both are pinned by model id and recorded in every result row. Determinism is
not assumed for either, which is exactly why we sample N times and report CIs.

GLM 5.2 availability check. The existing ~/bdpolicylab wiring pins glm-5.1.
The adapter will request glm-5.2; at build time we send one probe call and
confirm the z.ai endpoint accepts it. If 5.2 is not yet exposed, the runner
fails loudly with the endpoint error rather than silently downgrading to 5.1.
The user decides whether to wait or pin 5.1.

Rationale for CLI-based Opus: the user has a Claude Code subscription, not a
raw ANTHROPIC_API_KEY. The CLI headless print mode is the supported way to get
a one-shot completion under that subscription. The adapter shells out and
parses the JSON envelope ({"result": "...", ...}); claude --version is recorded
per run.

## 3. Architecture

```
econ-eval/
  pyproject.toml          # uv project: anthropic, pyyaml, numpy, pytest
  tasks/                  # one YAML per task (the benchmark itself)
  econ_eval/
    __init__.py
    models.py             # Task, Sample, Grade, Result dataclasses
    adapters/
      base.py             # Adapter protocol: run(prompt) -> Completion
      opus.py             # claude CLI headless adapter
      glm.py              # z.ai anthropic-SDK adapter
    graders/
      numeric.py          # numeric-tolerance grader (objective)
      exact.py            # normalized exact-match grader (objective)
      code_exec.py        # run code in sandbox, assert tests pass (objective)
      judge.py            # rubric + blind pairwise LLM judge (subjective)
    stats.py              # bootstrap CIs, paired win-rate, sign test
    runner.py             # orchestrate: tasks x models x N samples -> results
    report.py             # markdown leaderboard + matplotlib cost/quality plot
  results/                # raw transcripts (jsonl) + scored sqlite, committed
  data/                   # symlinks/copies of source data for quant tasks
  tests/                  # pytest: graders, stats, adapters (mocked)
  Makefile                # make eval / make report / make test
  README.md
```

Each unit has one job and a typed interface:
- An Adapter turns a prompt string into a Completion {text, tokens_in,
  tokens_out, latency_s, raw}. It knows nothing about tasks or grading.
- A Grader turns (Task, completion_text) into a Grade {score in [0,1],
  passed: bool, detail}. Objective graders are pure functions; the judge grader
  is itself an Adapter call.
- The runner is the only place that knows about all three. It is deterministic
  given cached samples (resumable).

## 4. Task format

```yaml
id: quant-baci-bgd-rmg-2022
track: quantitative          # quantitative | reasoning | coding | writing
prompt: |
  Using BACI HS92 2022 (values in thousands USD), what was Bangladesh's
  total export value of HS 6109 (T-shirts) to the world? Answer with a
  single number in thousands USD.
grader:
  type: numeric              # numeric | exact | code_exec | judge
  reference: 8412034         # ground truth, computed from raw parquet
  tolerance_pct: 0.5         # |answer-ref|/ref <= 0.005 passes
source: "~/tradeweave/data/parquet/baci/... (computed 2026-06-22)"
samples: 5                   # N runs per model (default from config)
```

- track groups results in the report.
- grader.type selects the grader; remaining keys are grader-specific.
- source is mandatory and is a real, verifiable provenance string. No task
  ships without a traced reference value (data-integrity rule).
- Reference values for quantitative tasks are computed once by a small
  scripts/build_references.py against the user's own parquet/BACI/IMF/FRED, and
  the computed number plus the query is committed. The grader never recomputes
  at eval time; it compares against the frozen reference.

## 5. Four tracks (initial 12 tasks, 3 each)

1. Quantitative — compute or interpret a real trade/macro figure with a
   verifiable numeric answer. Grader: numeric tolerance. Objective.
2. Reasoning — an economic scenario or policy tradeoff; the answer is judged
   against a rubric of must-hit points. Grader: judge (rubric + blind pairwise).
   Subjective.
3. Coding — a small task in the user's stack (pandas/DuckDB/FastAPI snippet, or
   fix a bug). Grader: code_exec — the model's code is run and assertions must
   pass. Objective.
4. Writing — a short policy brief or Bangla op-ed paragraph. Grader: judge
   rubric (register, accuracy, no-slop) + a human spot-check field. Subjective.

Tasks are authored from the user's own data and recent (post-cutoff) events to
avoid contamination. The initial 12 are a seed; the harness scales to any count.

## 6. Grading detail (the part most evals get wrong)

- Objective graders (quantitative, coding) carry no model bias. Prefer these
  wherever a verifiable answer exists. The numeric grader extracts the final
  number robustly (a tagged ANSWER: line if present, else the last number) and
  applies tolerance_pct. The code grader writes the model's code to a temp file
  in an isolated subprocess with a CPU/time limit and runs the task assertions.
- Judge grader (reasoning, writing) uses a strong neutral instruction set:
  1. Rubric scoring — the judge scores each must-hit rubric point 0/1 and
     returns a fraction.
  2. Blind pairwise — the two models' answers are presented as "A" and "B" with
     identities stripped; the judge picks the better one. Run twice with A/B
     swapped and average, to cancel position bias.
  - Self-preference is the known hazard: a contestant judging itself inflates.
    Mitigations, in order: (a) maximize objective graders so the judge covers
    only the two subjective tracks; (b) the judge runs blind, so it cannot
    favour by name; (c) the judge model is a third, neutral model (see 10.1),
    not either contestant; plus a human_spotcheck column the user fills for a
    sampled subset.

## 7. Statistics

For each (task, model) we have N grades in [0,1].
- Per-model score = mean over tasks of per-task mean, with a bootstrap 95% CI
  (resample tasks, then samples).
- Head-to-head: per task, compare the two models' mean scores; the win-rate is
  the fraction of tasks A beats B, with a two-sided sign test p-value.
- The report states the win-rate, the CI overlap, and whether the difference is
  significant at alpha=0.05. No "Opus wins" / "GLM wins" claim is made if CIs
  overlap.
- Cost/latency are tracked per sample; the report includes a cost-per-correct
  figure and a quality-vs-cost scatter so the cheap-consult tradeoff is visible.

## 8. Reproducibility

- Model ids, CLI version, SDK version, and the full task set are recorded in
  every results file.
- Raw transcripts (every prompt and completion) are written to
  results/transcripts-<date>.jsonl and committed. Scored rows go to
  results/scores.sqlite (the user's default DB).
- The runner is resumable: a completed (task, model, sample) is cached by a
  content hash of (task id, prompt, model id); re-running re-grades from cache
  and only fills missing samples. Same task set + same cache -> identical report.
- All gitignored data (parquet copies under data/, large transcripts) is added
  to backup.sh/restore.sh per the user's backup rule.

## 9. Workflow

- make eval — run all tasks x both models x N samples, grade, write results.
- make report — build results/report-<date>.md + the cost/quality plot.
- make test — pytest the graders, stats, and adapters (adapters mocked; one
  optional live smoke test behind a flag).
- Cost guard: the runner prints an estimated token/cost total and the task count
  before running, and supports --dry-run and --task <id> for a single task.

## 10. Open decisions (resolve in spec review)

1. Judge model. The methodologically cleanest choice is a third neutral model
   for the subjective tracks (avoids either contestant's self-preference).
   Already-wired options: DeepSeek V4 or Kimi K2.6. Recommendation: DeepSeek V4
   as the fixed judge, with human spot-check. Needs user confirmation.
2. Initial task authoring. The 12 seed tasks need real reference values. I will
   draft them from TradeWeave parquet / BACI / IMF and the user verifies each
   reference before they are committed (no unverified task ships).
3. Bangla writing track. Keep it in the seed set, or start English-only and add
   Bangla once the harness is proven? Recommendation: include one Bangla task in
   the seed to exercise the judge on register.

## 11. Quality gate

Every committed task reference traces to a primary source (BACI/IMF/FRED/raw
parquet). Numbers in the report are re-derived by stats.py and unit-tested. No
fabricated reference values, no placeholder tasks, no "X wins" claim without a
passing significance test. This binds the whole repo.
