#!/usr/bin/env bash
# The 2026-10-13 Muse Wonder run: muse-wonder (contributor lane) and muse-wonder-full
# over the 50 leaderboard-B tasks (every task except the agent track). Three workers
# per model, each taking every third task id, so transcript files never interleave.
#
# Two steps, because on 2026-10-13 muse was signed in only on galaxy (Windows) and
# codex (the Astra judge used for leaderboard B on 2026-09-15) only on ms5:
#   1. galaxy: MUSE_CLI=<muse-bin exe> scripts/run_2026_10_13.sh   (JUDGE=defer)
#   2. ms5:    JUDGE=astra uv run python scripts/regrade_judge.py results/transcripts-2026-10-13-*.jsonl
# Usage: scripts/run_2026_10_13.sh [date]
cd "$(dirname "$0")/.." || exit 1
unset ANTHROPIC_API_KEY
export JUDGE=${JUDGE:-defer}
export PYTHONUTF8=1   # Bangla task files and muse session logs are UTF-8 (Windows default is cp1252)
DATE=${1:-2026-10-13}
LOG="results/logs-$DATE"
mkdir -p "$LOG"
mapfile -t TASKS < <(ls tasks/*.yaml | xargs -n1 basename | sed 's/\.yaml$//' | grep -v '^agent-')
echo "${#TASKS[@]} tasks, judge=$JUDGE"
for m in muse-wonder muse-wonder-full; do
  for i in 0 1 2; do
    (
      for ((j = i; j < ${#TASKS[@]}; j += 3)); do
        uv run python -m econ_eval --date "$DATE-$m-w$i" eval --models "$m" --task "${TASKS[j]}"
      done
    ) > "$LOG/$m-$i.log" 2>&1 &
  done
done
wait
echo "all workers done $(date '+%F %H:%M')"
tail -n 1 "$LOG"/*.log
