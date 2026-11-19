#!/bin/zsh
# The 2026-11-19 Gemini 4 Neon run: gemini-4-neon-low and gemini-4-neon-high (agy) over the
# 50 leaderboard-B tasks (every task except the agent track), graded by the Opus 5.5 judge (JUDGE=opus55).
# A small run: N samples per task (default 2; 1 for Argon on 2026-10-15, 2 for Wonder,
# 5 for the earlier models), W workers per model, each taking every Wth task id so transcript files
# never interleave. Runs in one step on a machine with agy and the claude CLI signed in.
# Usage: [MODELS="..."] [N=2] scripts/run_2026_11_19.sh [date]
cd "$(dirname "$0")/.." || exit 1
unset ANTHROPIC_API_KEY
export JUDGE=${JUDGE:-opus55}
DATE=${1:-2026-11-19}
N=${N:-2}
W=${W:-5}
MODELS=(${=MODELS:-gemini-4-neon-low gemini-4-neon-high})
LOG="results/logs-$DATE"
mkdir -p "$LOG"
TASKS=(${(f)"$(ls tasks/*.yaml | xargs -n1 basename | sed 's/\.yaml$//' | grep -v '^agent-')"})
echo "${#TASKS[@]} tasks, n=$N, $W workers per model, judge=$JUDGE, models=${MODELS[*]}"
for m in $MODELS; do
for ((i = 0; i < W; i++)); do
  (
    for ((j = i + 1; j <= ${#TASKS[@]}; j += W)); do
      uv run python -m econ_eval --date "$DATE-$m-w$i" eval --models "$m" --task "${TASKS[j]}" -n "$N"
    done
  ) > "$LOG/$m-$i.log" 2>&1 &
done
done
wait
echo "all workers done $(date '+%F %H:%M')"
tail -n 1 "$LOG"/*.log
