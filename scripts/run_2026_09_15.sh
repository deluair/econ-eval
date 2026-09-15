#!/bin/zsh
# The 2026-09-15 "daily work" run: five contestants over all 50 tasks, sharded workers
# sharing results/scores.sqlite (busy_timeout 60 s). Transcripts land in
# results/transcripts-<date>-<model>-shardIofK.jsonl (gitignored, back up with backup.sh).
# Usage: scripts/run_2026_09_15.sh [date]
cd "$(dirname "$0")/.."
# DEEPSEEK_API_KEY comes from the machine config (Keychain resolver); source it before
# `set -u`, which aborts the resolver on an unbound variable (first launch, 2026-09-15).
# Never export ANTHROPIC_API_KEY here: the CLI judge must stay on the Claude subscription.
source "$HOME/dotfiles/config.sh" >/dev/null 2>&1 || true
export DEEPSEEK_API_KEY   # config.sh assigns without exporting; children need it
unset ANTHROPIC_API_KEY
set -u
[ -n "${DEEPSEEK_API_KEY:-}" ] || echo "WARN: DEEPSEEK_API_KEY unset; deepseek-flash shards will fail"
DATE=${1:-2026-09-15}
LOG="results/logs-$DATE"
mkdir -p "$LOG"
for m in fable astra gemini-3.8-flash muse; do
  for i in 0 1 2; do
    uv run python -m econ_eval --date "$DATE" eval --models "$m" --shard "$i/3" > "$LOG/$m-$i.log" 2>&1 &
  done
done
for i in 0 1; do
  uv run python -m econ_eval --date "$DATE" eval --models deepseek-flash --shard "$i/2" > "$LOG/deepseek-flash-$i.log" 2>&1 &
done
wait
echo "all shards done $(date '+%F %H:%M')"
tail -n 1 "$LOG"/*.log
