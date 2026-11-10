#!/bin/zsh
# The 2026-11-09 Muse Ember run: muse-ember (Muse subscription, muse-ember-1.0, default
# high effort) over the 50 leaderboard-B tasks (every task except the agent track),
# graded by the Astra judge. N samples per task (5, matching Muse Spark 1.3), W workers,
# each taking every Wth task id so transcript files never interleave. Runs in one step
# on a machine with both muse and codex signed in.
# Usage: scripts/run_2026_11_09.sh [date]
cd "$(dirname "$0")/.." || exit 1
unset ANTHROPIC_API_KEY
export JUDGE=${JUDGE:-astra}
DATE=${1:-2026-11-09}
N=${N:-5}
W=${W:-2}
m=muse-ember
LOG="results/logs-$DATE"
mkdir -p "$LOG"
TASKS=(${(f)"$(ls tasks/*.yaml | xargs -n1 basename | sed 's/\.yaml$//' | grep -v '^agent-')"})
echo "${#TASKS[@]} tasks, n=$N, $W workers, judge=$JUDGE"
for ((i = 0; i < W; i++)); do
  (
    for ((j = i + 1; j <= ${#TASKS[@]}; j += W)); do
      uv run python -m econ_eval --date "$DATE-$m-w$i" eval --models "$m" --task "${TASKS[j]}" -n "$N"
    done
  ) > "$LOG/$m-$i.log" 2>&1 &
done
wait
echo "all workers done $(date '+%F %H:%M')"
tail -n 1 "$LOG"/*.log
