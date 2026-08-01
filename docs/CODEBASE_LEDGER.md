# econ-eval Codebase Ledger

Standing map of architecture truths, conventions, and known quirks. Read before
any audit; write findings back here, dated.

## Architecture truths

- Adapters (2026-07-31): `opus.py` = Claude CLI headless (`-p --output-format
  json --model <id>`), used for the opus contestant AND the Fable judge.
  `glm.py` = Anthropic-SDK client against Anthropic-compatible endpoints (z.ai
  GLM, DeepSeek). `openrouter.py` = one OpenAI-compatible endpoint for the
  cheap-model fleet, key from `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`),
  max_tokens 16384 because reasoning models spend output tokens on thinking.
- Cache: `results/scores.sqlite` is git-tracked and keyed (task_id, model,
  idx); the runner only fills missing rows. Transcripts are gitignored,
  backed up to `$GDRIVE/econ-eval` via backup.sh.
- Parallelism: one `eval --models <name>` process per model is safe; the
  runner sets `PRAGMA busy_timeout=60000` (added 2026-07-31).
- Judge: Claude Opus 5 (`claude-opus-5`) via the CLI since 2026-08-01. History:
  DeepSeek V4 flash -> Fable 5 (2026-07-31, "judge not from openrouter") ->
  Opus 5 (user instruction, after the Fable 7-day quota was exhausted). Every
  judge switch requires regrading ALL judge rows, not just ungraded ones;
  `DONE_PREFIX` in regrade_judge.py enforces this by design.

## Data/unit conventions

- PRICES in config.py are USD per 1M tokens. OpenRouter entries read from
  https://openrouter.ai/api/v1/models on 2026-07-31, keyed by the full
  OpenRouter id (which is what the DB `model` column stores for fleet rows).
- Opus token counts include the whole Claude Code harness context (README cost
  caveat); not comparable to bare API token counts.

## Resolved (dated)

- 2026-07-31: OpusAdapter previously omitted `--model`, so it ran whatever the
  CLI's default model was. Pinned to `claude-opus-4-8` explicitly. Historical
  opus rows (June, July 30 runs) were generated when the CLI default was Opus
  4.8, so cached rows are correctly labeled.
- 2026-08-01: all 500 judge rows regraded by Opus 5 in one pass, so the
  subjective tracks carry a single judge. Rows carry an "opus5-judge" prefix in
  scores.detail. The earlier partial Fable pass (198 rows) was fully
  overwritten; no mixed-judge scores survive.
- 2026-07-31: Opus/GLM completions for the 4 judge tasks added 2026-07-30
  (reason-passthrough-netting, reason-rca-interpretation, write-bangla-formal,
  write-tight-constraints) could not be regraded from transcripts (that run's
  transcripts live only on the machine that ran it, never backed up) and were
  regenerated fresh instead.

## Open issues

- 2026-08-01, LOW: the judge (Opus 5) and one contestant (Opus 4.8) are from
  the same family, so subjective scores for the opus row are not independently
  refereed. Objective tracks are immune (deterministic graders). Stated in the
  README; revisit if a neutral judge with sufficient quota becomes available.
- 2026-08-01, LOW: objective tracks are saturated (6 of 10 models at exactly
  1.000, no sign test clears alpha=0.05). Discrimination now comes from one
  task, quant-rca-6109. Add multi-step tasks where an early unit error
  propagates before drawing further conclusions from this half.

## Known-intentional quirks

- The `claude` CLI signals credit exhaustion two different ways: exit 1 with
  EMPTY stderr, or exit 0 with an `api_error` result envelope carrying HTTP
  429. The empty-stderr form is easy to misread as a concurrency fault. It is
  not: 16 concurrent CLI calls run fine (~95 judge rows/min against ~6/min at
  3 workers). Tell them apart by whether retries make progress; a credit wall
  fails every retry instantly with zero rows done. Worker count is set by
  `REGRADE_WORKERS` (default 16).
- Task files are append-only so cached completions stay valid; never edit an
  existing task prompt without wiping its cached rows.
- June 2026 transcripts (12 tasks) are the only local record of the June
  opus/glm completions; keep `results/transcripts-2026-06-22.jsonl` backed up.
