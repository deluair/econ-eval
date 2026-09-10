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
- Contestant `deepseek-flash` (2026-09-10): DeepSeek V4.1 Flash via the direct
  DeepSeek Anthropic-compatible endpoint (`ZAIAdapter`, max_tokens 16384 to
  leave room for hidden thinking, which the endpoint bills as output tokens).
  `deepseek-flash` is DeepSeek's canonical id for V4.1 Flash since 2026-09-10;
  `deepseek-v4-flash` is retired and routed to it, and `deepseek-v4-pro` will
  be too from 2026-09-14 (api-docs.deepseek.com/updates). Chosen over the
  OpenRouter route because OpenRouter served `deepseek/deepseek-v4.1-flash`
  from a third-party host (Novita) in the smoke test.
- Contestant `muse` (2026-09-10): Meta Muse Spark 1.3 through the Muse Code CLI
  on the user's subscription (`muse.py`, `muse exec --json --session-id <uuid>`
  from an empty scratch dir). Final text comes from the `run.terminal.completed`
  event; usage is NOT in that stream, it is summed from the CLI's own session
  store (`~/.local/share/muse/sessions/Y/M/D/<sid>/session.jsonl`,
  `payload.event.kind == model_completed`). The subscription lane serves
  `muse-spark-1.3-contributor`; the adapter raises if the served model id
  differs. It is an agent with tools (it ran its own tests on code tasks), so
  input tokens are ~57k per call, mostly cache reads, like the Opus CLI row.

## Data/unit conventions

- PRICES in config.py are USD per 1M tokens. OpenRouter entries read from
  https://openrouter.ai/api/v1/models on 2026-07-31, keyed by the full
  OpenRouter id (which is what the DB `model` column stores for fleet rows).
- Opus token counts include the whole Claude Code harness context (README cost
  caveat); not comparable to bare API token counts.

## Resolved (dated)

- 2026-09-10: DeepSeek V4.1 Flash run, 100 completions, 0.992 overall
  [0.975, 1.000], first model above Opus 4.8 (0.979); sign test vs Opus
  p=0.375 (4 wins, 1 loss on the 5 writing tasks where they differ). Cost by
  token count $0.0803 at the off-peak price; DeepSeek balance fell $0.07 (the
  run was 15:48 to 16:05 UTC, off-peak; 5 identical prompts per task hit the
  input cache). Judge Opus 5, same as the 2026-08-01 rows.
- 2026-09-10: Muse Spark 1.3 run, 100 completions, 0.972 overall [0.930,
  1.000], 4th; sign test vs Opus p=0.727 (5 wins, 3 losses). Perfect on
  quantitative and both Bangla tasks, tops writing (0.980). Two coding zeros,
  both format: the agent appended its own verification output to code it was
  told to return alone (code-rca idx 0 unfenced prose; code-cagr idx 0 test
  output in the largest fence). Cost column $0.60 is notional (contributor API
  price on CLI token counts); the run was subscription prompts.
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

- The runner's inline judge path writes `detail` WITHOUT the `opus5-judge`
  prefix that regrade_judge.py stamps, so a fresh model's judge rows look
  un-regraded to that script. For the 2026-09-10 run the 50 rows were stamped
  by hand (`UPDATE scores SET detail='opus5-judge '||detail ...`) after the run,
  since the judge was already Opus 5. Do the same for any new model, or run
  regrade_judge.py on its transcript (which re-spends the judge calls).
- The `claude` CLI judge FAILS if `ANTHROPIC_API_KEY` is in the environment
  (it prefers the key over the subscription login and the key in config.sh is
  not valid): "claude.ai connectors are disabled because ANTHROPIC_API_KEY or
  another auth source is set". Export only the contestant keys; never
  `set -a; source config.sh` before an eval. Cost of learning this 2026-09-10:
  five workers burned 9 minutes of judge retries with zero rows written.
- The user's SessionStart routine hook prepends its card text to every CLI
  answer, judge included. `_parse_json` finds the JSON object anyway, so
  grades are unaffected, but transcripts of judge output would carry it.
- `muse exec` in headless mode HANGS when the agent proposes a bash tool call:
  it enters `approval_wait` and nothing answers. One code-cagr call on
  2026-09-10 sat the full 600 s timeout. Adapter timeout is now 180 s (a normal
  call is 30 to 60 s) and the retry loop opens a fresh session. The clean fix,
  `--disable-approval --user-input-auto-resolve` on the exec command, could
  not be committed from the Claude Code background job because its auto-mode
  classifier refuses to write a flag that disables another tool's approvals;
  add it by hand if hangs recur (the user approved it on 2026-09-10).
- The runner buffers transcript writes until the process exits, so a task's
  transcript file is empty while its 5 samples run; read the Muse session
  store (or the DB) for in-flight inspection.
- Parallel runs of ONE model: give each worker its own `--date` suffix so the
  per-worker transcript files never interleave, then concatenate them (done
  2026-09-10, 5 workers x 4 tasks, 17 min wall clock for 100 completions).
- The `claude` CLI signals credit exhaustion two different ways: exit 1 with
  EMPTY stderr, or exit 0 with an `api_error` result envelope carrying HTTP
  429. The empty-stderr form is easy to misread as a concurrency fault. It is
  not: 16 concurrent CLI calls run fine. Tell them apart by whether retries
  make progress; a credit wall fails every retry instantly with zero rows done.
- Regrade throughput, measured 2026-08-01 by wall clock (`REGRADE_WORKERS`):
  3 workers = 98 rows in 231s (25.5 rows/min); 16 workers = 402 rows in 208s
  (116 rows/min). That is 4.6x, NOT the 5.3x that worker count alone implies:
  scaling is sublinear because per-call CLI startup dominates. Do not quote a
  linear projection. Default is 16.
- Task files are append-only so cached completions stay valid; never edit an
  existing task prompt without wiping its cached rows.
- June 2026 transcripts (12 tasks) are the only local record of the June
  opus/glm completions; keep `results/transcripts-2026-06-22.jsonl` backed up.

## Branch cleanup

2026-08-10 branch cleanup (Claude): worktree-openrouter-cheap-models (tip 106e732) deleted local+remote without re-merging: PR #2 is MERGED (squash-merge, so git ancestry did not show it landed). Worktree .claude/worktrees/openrouter-cheap-models was clean: unlocked and removed. Goal state reached: only main remains local and on origin.
