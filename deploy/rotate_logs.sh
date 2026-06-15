#!/usr/bin/env sh
set -eu

DEFAULT_ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="${ASSET_MANAGER_ENV:-$DEFAULT_ROOT_DIR/deploy/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

ROOT_DIR="${NAS_PROJECT_DIR:-$DEFAULT_ROOT_DIR}"
LOG_DIR="$ROOT_DIR/logs"
RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"

if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory not found: $LOG_DIR"
  exit 0
fi

echo "Log files older than $RETENTION_DAYS days:"
find "$LOG_DIR" -type f -name "*.log" -mtime +"$RETENTION_DAYS" -print

if [ "${DELETE_OLD_LOGS:-false}" = "true" ]; then
  find "$LOG_DIR" -type f -name "*.log" -mtime +"$RETENTION_DAYS" -delete
  echo "Old log files deleted."
else
  echo "No files deleted. Set DELETE_OLD_LOGS=true to delete after review."
fi
