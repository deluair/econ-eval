#!/bin/zsh
set -eu

cd "$(dirname "$0")/.."
export JUDGE=astra
unset ANTHROPIC_API_KEY
DATE="2026-09-15"
LOG="results/logs-$DATE"
mkdir -p "$LOG"

echo "Starting 3 parallel fill workers for gemini-3.8-flash with JUDGE=astra at $(date '+%H:%M:%S')"

w0=(
  reason-terms-of-trade
  reason-taka-depreciation
  review-agent-brief
  write-abstract-150
  write-bangla-formal
)

w1=(
  review-consistency
  review-referee-comment
  review-systemd-timer
  write-bangla-plain-remittance
  write-cover-paragraph
  write-exec-summary
)

w2=(
  write-oped-bangla
  write-policy-brief
  write-recruiter-reply
  write-tight-constraints
  write-x-post
)

(
  for t in "${w0[@]}"; do
    echo "[worker 0] starting $t at $(date '+%H:%M:%S')"
    uv run python -m econ_eval --date "$DATE" eval --models gemini-3.8-flash --task "$t" -n 5 >> "$LOG/gemini-fill-w0.log" 2>&1
  done
  echo "[worker 0] finished at $(date '+%H:%M:%S')"
) &
p0=$!

(
  for t in "${w1[@]}"; do
    echo "[worker 1] starting $t at $(date '+%H:%M:%S')"
    uv run python -m econ_eval --date "$DATE" eval --models gemini-3.8-flash --task "$t" -n 5 >> "$LOG/gemini-fill-w1.log" 2>&1
  done
  echo "[worker 1] finished at $(date '+%H:%M:%S')"
) &
p1=$!

(
  for t in "${w2[@]}"; do
    echo "[worker 2] starting $t at $(date '+%H:%M:%S')"
    uv run python -m econ_eval --date "$DATE" eval --models gemini-3.8-flash --task "$t" -n 5 >> "$LOG/gemini-fill-w2.log" 2>&1
  done
  echo "[worker 2] finished at $(date '+%H:%M:%S')"
) &
p2=$!

wait $p0 $p1 $p2
echo "All 3 fill workers complete at $(date '+%H:%M:%S')"
sqlite3 results/scores.sqlite "SELECT COUNT(*) FROM scores WHERE model='gemini-3.8-flash-high';"
