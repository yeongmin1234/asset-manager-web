#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/frontend.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "Frontend pid file not found. Nothing to stop."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Frontend stop signal sent. pid=$PID"
else
  echo "Frontend process is not running. pid=$PID"
fi

rm -f "$PID_FILE"
