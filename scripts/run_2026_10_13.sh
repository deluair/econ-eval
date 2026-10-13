#!/bin/zsh
# The 2026-10-13 Muse Wonder run: muse-wonder (contributor lane) and muse-wonder-full
# over the 50 leaderboard-B tasks (every task except the agent track), Astra judge as
# on 2026-09-15. Three workers per model, each taking every third task id, so the
# transcript files never interleave. Usage: scripts/run_2026_10_13.sh [date]
cd "$(dirname "$0")/.."
unset ANTHROPIC_API_KEY
export JUDGE=astra
set -u
DATE=${1:-2026-10-13}
LOG="results/logs-$DATE"
mkdir -p "$LOG"
TASKS=(${(f)"$(ls tasks/*.yaml | xargs -n1 basename | sed 's/\.yaml$//' | grep -v '^agent-')"})
echo "${#TASKS} tasks"
for m in muse-wonder muse-wonder-full; do
  for i in 0 1 2; do
    (
      for ((j = i + 1; j <= ${#TASKS}; j += 3)); do
        uv run python -m econ_eval --date "$DATE-$m-w$i" eval --models "$m" --task "${TASKS[j]}"
      done
    ) > "$LOG/$m-$i.log" 2>&1 &
  done
done
wait
echo "all workers done $(date '+%F %H:%M')"
tail -n 1 "$LOG"/*.log
