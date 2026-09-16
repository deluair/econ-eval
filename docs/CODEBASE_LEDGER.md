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

- Contestants `fable`, `astra`, `gemini-3.8-flash` (2026-09-15): all subscription
  CLIs. `fable` = OpusAdapter on `claude-fable-5-1` (Claude Max, access ends
  2026-09-23). `astra` = `codex.py`, `codex exec --skip-git-repo-check --json -m
  gpt-6-astra -c model_reasoning_effort=high` from an empty scratch dir; final
  text is the last `item.completed` agent_message, usage from `turn.completed`
  (about 25k harness input tokens per call). `gemini-3.8-flash` = `agy.py`,
  `agy -p --output-format json --model gemini-3.8-flash-high --disable-slash-commands`
  from an empty scratch dir; text in `response`, usage in `usage` (about 13k
  harness input tokens), `status` must be SUCCESS (a 503 "No capacity" returns
  status ERROR with text still filled and is retried). The agy prompt carries a
  PREAMBLE telling the agent to answer in the reply and touch no files: without
  it Gemini tried `read_file` on "return only the code" prompts, print mode
  auto-denied it, and the reply came back empty (every coding task 0.0,
  reproduced 2026-09-15). Same class of accommodation as the Muse adapter.
- `eval --shard i/k` (2026-09-15) partitions the task list by index modulo k so
  k workers of one model can run at once against the shared sqlite cache; each
  worker writes `transcripts-<date>-<model>-shardIofK.jsonl`. Launcher for the
  2026-09-15 run: `scripts/run_2026_09_15.sh` (3 shards per CLI model, 2 for
  DeepSeek).
- Tracks (2026-09-15): `finance` and `review` added to `VALID_TRACKS` and to
  `report.TRACKS`; 50 tasks = 20 original + 30 "daily work" tasks whose
  references come from `scripts/build_references_daily.py` (BACI 2013/2022/2023
  and WTO MFN lines via TradeWeave parquet, NY Fed ACM via FinObservatory
  parquet, and author-defined arithmetic) and whose yamls were emitted by
  `scripts/gen_tasks_2026_09_15.py`.

- Hugging Face export (2026-09-16): `scripts/export_hf.py --out DIR
  --transcripts "$GDRIVE/econ-eval/results" --transcripts results` writes
  `DIR/dataset` (tasks.jsonl, scores.csv with `judge` and `task_set` columns,
  transcripts.jsonl, leaderboard/tracks CSVs, plots, dataset card) and
  `DIR/space` (static index.html from `scripts/hf_space_template.html`, data
  embedded). Upload with `hf upload deluair/econ-eval DIR/dataset . --repo-type
  dataset` and `... DIR/space . --repo-type space`. Two leaderboards, never
  merged: A = 20 original tasks, 12 models, Opus 5 judge; B = 50 tasks, the
  five 2026-09-15 contestants, Astra judge except the cached Opus-5 rows of
  deepseek-flash and muse on the original 20 (the `judge` column records it).
  B excludes the agent pilot task, so DeepSeek reads 0.960 there against 0.961
  in report-2026-09-15.md. Transcript score fields are overwritten from the
  DB at export (June rows were regraded 2026-08-01). Coverage: 1,403 of 2,238
  completions have transcripts (the 2026-08-01 OpenRouter fleet has none).
  The export reproduces every README leaderboard A number exactly (checked
  2026-09-16).

## Data/unit conventions

- PRICES in config.py are USD per 1M tokens. OpenRouter entries read from
  https://openrouter.ai/api/v1/models on 2026-07-31, keyed by the full
  OpenRouter id (which is what the DB `model` column stores for fleet rows).
- Opus token counts include the whole Claude Code harness context (README cost
  caveat); not comparable to bare API token counts.

## Resolved (dated)

- 2026-09-15: 50-task expanded daily-work benchmark (250 completions per model)
  completed across 5 primary subscription and API contestants with Astra judge
  (`export JUDGE=astra` via `CodexAdapter` after Claude CLI judge credit limits).
  Standings: (1) `gpt-6-astra` 0.983 [0.966, 0.997]; (2) `gemini-3.8-flash-high`
  0.977 [0.950, 0.998], perfect 1.000 on quantitative (55/55), finance (25/25),
  and coding (50/50), 0.996 on reasoning, 0.942 writing, 0.868 review, sign test
  vs Astra p=1.0000 (no significant difference); (3) `muse-spark-1.3-contributor`
  0.966 [0.938, 0.988]; (4) `deepseek-flash` 0.961 [0.920, 0.991]; (5)
  `claude-fable-5-1` 0.948 [0.913, 0.979] (232 rows).
  Gemini 3.8 Flash run was completed from Antigravity CLI after Muse CLI stalled
  due to its sandbox denying localhost `bind()` syscalls required by `agy`.

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
- `~/dotfiles/config.sh` assigns `DEEPSEEK_API_KEY` without exporting it, and
  its Keychain resolver aborts under `set -u`. A launcher must `source` it
  before `set -u` and then `export DEEPSEEK_API_KEY` explicitly, or every
  DeepSeek worker dies with "DEEPSEEK_API_KEY is not set" after printing its
  task count (two wasted launches, 2026-09-15). `run_2026_09_15.sh` does both.
- On Claude Fable 5.1 and GPT-6 Astra the objective tracks were solved at
  1.000 through the first 100 rows (2026-09-15); the writing/review judge rows
  are where they separate, same shape as the 2026-08-01 finding.
- June 2026 transcripts (12 tasks) are the only local record of the June
  opus/glm completions; keep `results/transcripts-2026-06-22.jsonl` backed up.

## Branch cleanup

2026-08-10 branch cleanup (Claude): worktree-openrouter-cheap-models (tip 106e732) deleted local+remote without re-merging: PR #2 is MERGED (squash-merge, so git ancestry did not show it landed). Worktree .claude/worktrees/openrouter-cheap-models was clean: unlocked and removed. Goal state reached: only main remains local and on origin.

## Agent track pilot (2026-09-15, Muse session)

- New `agent` track: contestants run a tool loop (`agent_loop.py`: read_file,
  write_file, run_python sandboxed in a per-sample temp workdir, delegate
  depth-1 sub-call; ```tool <name> fences, FINAL ends, max_steps 12) instead
  of one-shot completion. Runner stages `tasks/files/<id>/` into the workdir
  when track == agent; transcripts carry the tool `trace`.
- New `artifact` grader (deterministic, no judge spend): numeric-on-file and
  assertions-on-file. 4 pilot tasks, all references independently re-derived
  from seed files: agent-messy-csv 86.0671, agent-fix-script -10337.003,
  agent-reconcile 1.3952, agent-multistep 315.9276.
- `scripts/speed.py`: offline latency table + `--check id=sec` gate over
  scores.sqlite (makes no model calls). p95 = linear interpolation.
- Live proof 2026-09-15: deepseek-flash solved agent-messy-csv idx 0 end to
  end (33.4 s, 1.0). Suite 105 passed.
