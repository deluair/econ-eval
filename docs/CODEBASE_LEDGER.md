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
- Judge (since 2026-07-31): Claude Fable 5 via the CLI, per user instruction
  ("use yourself as judge, fable from here", "judge not from openrouter").
  Before that: DeepSeek V4 flash. Caveat: Anthropic model judging an Anthropic
  contestant is not neutral; noted in README.

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
- 2026-07-31: judge switched DeepSeek -> Fable mid-project. All judge-track
  rows re-graded by Fable from transcripts (scripts/regrade_judge.py) so no
  mixed-judge scores survive. Opus/GLM completions for the 4 judge tasks added
  2026-07-30 (reason-passthrough-netting, reason-rca-interpretation,
  write-bangla-formal, write-tight-constraints) could not be re-graded from
  transcripts (that run's transcripts live only on the machine that ran it,
  never backed up) and were regenerated fresh instead. Re-graded rows carry a
  "fable-judge" prefix in scores.detail.

## Open issues

- 2026-08-01, HIGH: subjective tracks (reasoning, writing) carry MIXED JUDGE
  scores and must not be reported. 198 of 500 rows regraded by Fable, 302 still
  DeepSeek. The regrade stalled because the Claude subscription hit its 7-day
  limit with overage disabled (`out_of_credits`, HTTP 429), resetting
  2026-08-03 12:00 UTC. All 1,000 completions are cached, so finishing costs
  judge calls only. Resume with
  `uv run python scripts/regrade_judge.py <transcripts...>`; the script skips
  rows already marked `fable-judge` in scores.detail.
- 2026-08-01, LOW: objective tracks are saturated (6 of 10 models at exactly
  1.000, no sign test clears alpha=0.05). Discrimination now comes from one
  task, quant-rca-6109. Add multi-step tasks where an early unit error
  propagates before drawing further conclusions from this half.

## Known-intentional quirks

- The `claude` CLI exits non-zero under concurrent invocation, and returns
  exit 0 with an `api_error` result envelope when out of credits. OpusAdapter
  retries 3x with backoff (2026-08-01); the regrade script runs 3 workers, not 6.
- Task files are append-only so cached completions stay valid; never edit an
  existing task prompt without wiping its cached rows.
- June 2026 transcripts (12 tasks) are the only local record of the June
  opus/glm completions; keep `results/transcripts-2026-06-22.jsonl` backed up.
