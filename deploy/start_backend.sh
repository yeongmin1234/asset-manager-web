#!/usr/bin/env sh
set -eu

DEFAULT_ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DEPLOY_ENV_FILE="${ASSET_MANAGER_ENV:-$DEFAULT_ROOT_DIR/deploy/.env}"

if [ -f "$DEPLOY_ENV_FILE" ]; then
  set -a
  . "$DEPLOY_ENV_FILE"
  set +a
fi

ROOT_DIR="${NAS_PROJECT_DIR:-$DEFAULT_ROOT_DIR}"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"

if [ -f "$BACKEND_ENV_FILE" ]; then
  set -a
  . "$BACKEND_ENV_FILE"
  set +a
fi

LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$LOG_DIR/backend.pid"
LOG_FILE="$LOG_DIR/backend.log"
BACKEND_DIR="$ROOT_DIR/backend"

mkdir -p "$LOG_DIR"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Backend venv not found: $BACKEND_DIR/.venv"
  echo "Create it first: cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

BACKEND_HOST="${BACKEND_HOST:-${HOST:-0.0.0.0}}"
BACKEND_PORT="${BACKEND_PORT:-${PORT:-8010}}"
. "$ROOT_DIR/deploy/backend_process.sh"

if [ -f "$PID_FILE" ]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if backend_pid_matches "$EXISTING_PID"; then
    echo "Existing asset-manager backend is running. Stop it before starting another. pid=$EXISTING_PID" >&2
    exit 1
  else
    echo "Removing stale backend pid file. pid=${EXISTING_PID:-unknown}"
    rm -f "$PID_FILE"
  fi
fi

if backend_port_status; then
  echo "Backend port $BACKEND_PORT is already in use; refusing to stop its listener." >&2
  for listener_pid in $(backend_listener_pids | sort -u); do
    if backend_pid_matches "$listener_pid"; then
      echo "Existing asset-manager backend listener: pid=$listener_pid" >&2
    else
      echo "Unrelated or unverifiable listener: pid=$listener_pid" >&2
    fi
  done
  exit 1
else
  port_result=$?
  if [ "$port_result" -ne 1 ]; then
    echo "Cannot verify that backend port $BACKEND_PORT is free." >&2
    exit 1
  fi
fi

cd "$BACKEND_DIR"
. .venv/bin/activate
if ! python -c "from app.main import app; print('IMPORT_OK')"; then
  echo "Backend import check failed; startup cancelled." >&2
  exit 1
fi

echo "Backend CORS origins: ${CORS_ORIGINS:-<application defaults>}"
nohup python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" >> "$LOG_FILE" 2>&1 &
NEW_PID="$!"
echo "$NEW_PID" > "$PID_FILE"

attempt=1
while [ "$attempt" -le 15 ]; do
  sleep 1

  if ! backend_pid_matches "$NEW_PID"; then
    echo "Backend process exited or did not match the expected command during startup."
    tail -n 50 "$LOG_FILE" 2>/dev/null || true
    if kill -0 "$NEW_PID" 2>/dev/null; then
      echo "Unverified process is still running; retaining PID file for inspection. pid=$NEW_PID" >&2
    else
      rm -f "$PID_FILE"
    fi
    exit 1
  fi

  health_status="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$BACKEND_PORT/health" 2>/dev/null || true)"
  if [ "$health_status" = "200" ] && backend_pid_matches "$NEW_PID"; then
    echo "Backend started. pid=$NEW_PID, port=$BACKEND_PORT, log=$LOG_FILE"
    exit 0
  fi

  attempt=$((attempt + 1))
done

echo "Backend health check timed out."
tail -n 50 "$LOG_FILE" 2>/dev/null || true
if backend_pid_matches "$NEW_PID"; then
  kill "$NEW_PID" 2>/dev/null || true
fi
if kill -0 "$NEW_PID" 2>/dev/null; then
  echo "Backend process remains alive after timeout; retaining PID file. pid=$NEW_PID" >&2
else
  rm -f "$PID_FILE"
fi
exit 1
