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
PID_FILE="$LOG_DIR/frontend.pid"
LOG_FILE="$LOG_DIR/frontend.log"
DIST_DIR="$ROOT_DIR/frontend/dist"
STATIC_SERVER_SCRIPT="$ROOT_DIR/deploy/static_server.py"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Frontend is already running. pid=$(cat "$PID_FILE")"
  exit 0
fi

if [ ! -d "$DIST_DIR" ]; then
  echo "Frontend dist not found: $DIST_DIR"
  echo "Build it first: cd frontend && npm run build"
  exit 1
fi

FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3010}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn | grep -q ":$FRONTEND_PORT "; then
    echo "Frontend port $FRONTEND_PORT is already in use, but $PID_FILE is not active."
    echo "Stop the existing process/container that owns port $FRONTEND_PORT before starting frontend."
    exit 1
  fi
elif command -v netstat >/dev/null 2>&1; then
  if netstat -ltn | grep -q ":$FRONTEND_PORT "; then
    echo "Frontend port $FRONTEND_PORT is already in use, but $PID_FILE is not active."
    echo "Stop the existing process/container that owns port $FRONTEND_PORT before starting frontend."
    exit 1
  fi
fi

if [ -f "$STATIC_SERVER_SCRIPT" ]; then
  nohup "$PYTHON_BIN" "$STATIC_SERVER_SCRIPT" --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --directory "$DIST_DIR" >> "$LOG_FILE" 2>&1 &
else
  nohup "$PYTHON_BIN" -m http.server "$FRONTEND_PORT" --bind "$FRONTEND_HOST" --directory "$DIST_DIR" >> "$LOG_FILE" 2>&1 &
fi
echo "$!" > "$PID_FILE"

sleep 1
if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Frontend failed to stay running. Check log=$LOG_FILE"
  rm -f "$PID_FILE"
  exit 1
fi

echo "Frontend static server started. pid=$(cat "$PID_FILE"), port=$FRONTEND_PORT, log=$LOG_FILE"
