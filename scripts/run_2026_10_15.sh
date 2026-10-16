#!/bin/zsh
# The 2026-10-15 Gemini 4 Argon run: gemini-4-argon (agy, gemini-4-argon-high) over the
# 50 leaderboard-B tasks (every task except the agent track), graded by the Astra judge.
# A deliberately small run: N samples per task (1 on 2026-10-15, against 2 for Wonder and
# 5 for the earlier models), W workers, each taking every Wth task id so transcript files
# never interleave. Runs in one step on a machine with both agy and codex signed in.
# Usage: scripts/run_2026_10_15.sh [date]
cd "$(dirname "$0")/.." || exit 1
unset ANTHROPIC_API_KEY
export JUDGE=${JUDGE:-astra}
DATE=${1:-2026-10-15}
N=${N:-1}
W=${W:-5}
m=gemini-4-argon
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
