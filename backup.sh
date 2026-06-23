#!/usr/bin/env bash
# Back up gitignored data + transcripts to Google Drive ($GDRIVE).
set -euo pipefail
DEST="${GDRIVE:?set GDRIVE}/econ-eval"
mkdir -p "$DEST"
# scored sqlite is committed; transcripts and any local data copies are not
rsync -a --include='transcripts-*.jsonl' --exclude='*' results/ "$DEST/results/" 2>/dev/null || true
rsync -a data/ "$DEST/data/" 2>/dev/null || true
echo "backed up transcripts + data to $DEST"
