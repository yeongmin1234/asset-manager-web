#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$LOG_DIR/frontend.pid"
LOG_FILE="$LOG_DIR/frontend.log"
DIST_DIR="$ROOT_DIR/frontend/dist"
ENV_FILE="${ASSET_MANAGER_ENV:-$ROOT_DIR/deploy/.env}"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Frontend is already running. pid=$(cat "$PID_FILE")"
  exit 0
fi

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

if [ ! -d "$DIST_DIR" ]; then
  echo "Frontend dist not found: $DIST_DIR"
  echo "Build it first: cd frontend && npm run build"
  exit 1
fi

FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3010}"

nohup python3 -m http.server "$FRONTEND_PORT" --bind "$FRONTEND_HOST" --directory "$DIST_DIR" >> "$LOG_FILE" 2>&1 &
echo "$!" > "$PID_FILE"
echo "Frontend static server started. pid=$(cat "$PID_FILE"), log=$LOG_FILE"
