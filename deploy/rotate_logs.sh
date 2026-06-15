#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"

if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory not found: $LOG_DIR"
  exit 0
fi

find "$LOG_DIR" -type f -name "*.log" -mtime +"$RETENTION_DAYS" -print
echo "Review the files above before deleting. To delete after review, run:"
echo "find \"$LOG_DIR\" -type f -name \"*.log\" -mtime +\"$RETENTION_DAYS\" -delete"
