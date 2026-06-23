#!/usr/bin/env bash
set -euo pipefail
SRC="${GDRIVE:?set GDRIVE}/econ-eval"
[ -d "$SRC/results" ] && rsync -a "$SRC/results/" results/ || true
[ -d "$SRC/data" ] && rsync -a "$SRC/data/" data/ || true
echo "restored from $SRC"
