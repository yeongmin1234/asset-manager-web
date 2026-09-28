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

if [ ! -f "$DIST_DIR/index.html" ]; then
  echo "Frontend dist not found: $DIST_DIR"
  echo "Build it first: cd frontend && npm run build"
  exit 1
fi

if ! find "$DIST_DIR/assets" -maxdepth 1 -type f -name 'index-*.js' -print -quit 2>/dev/null | grep -q .; then
  echo "Frontend JS bundle not found: $DIST_DIR/assets/index-*.js"
  exit 1
fi

FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-3010}"
. "$ROOT_DIR/deploy/frontend_process.sh"

if command -v python3 >/dev/null 2>&1 &&
   python3 -c 'import sys' >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1 &&
     python -c 'import sys' >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Working Python interpreter not found (python3/python)."
  exit 1
fi

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if frontend_pid_matches "$PID"; then
    echo "Existing asset-manager frontend is running. Stop it before starting another. pid=$PID" >&2
    exit 1
  else
    echo "Removing stale frontend pid file. pid=$PID"
    rm -f "$PID_FILE"
  fi
fi

if frontend_port_status; then
  echo "Frontend port $FRONTEND_PORT is already in use; no listener was stopped." >&2
  exit 1
else
  port_result=$?
  if [ "$port_result" -ne 1 ]; then
    echo "Cannot verify that frontend port $FRONTEND_PORT is free." >&2
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
if ! frontend_pid_matches "$(cat "$PID_FILE")"; then
  echo "Frontend failed to stay running with the expected command. Check log=$LOG_FILE"
  if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Unverified process is still running; retaining PID file for inspection." >&2
  else
    rm -f "$PID_FILE"
  fi
  exit 1
fi

attempt=0
while [ "$attempt" -lt 10 ]; do
  if curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null && frontend_pid_matches "$(cat "$PID_FILE")"; then
    echo "Frontend static server started. pid=$(cat "$PID_FILE"), port=$FRONTEND_PORT, dist=$DIST_DIR, log=$LOG_FILE"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep 1
done

echo "Frontend process started but did not respond on port $FRONTEND_PORT."
exit 1
