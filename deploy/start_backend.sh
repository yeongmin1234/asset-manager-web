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
BACKEND_PORT="${BACKEND_PORT:-${PORT:-8001}}"

is_port_in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -q ":$BACKEND_PORT "
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | grep -q ":$BACKEND_PORT "
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v fuser >/dev/null 2>&1; then
    fuser "$BACKEND_PORT/tcp" >/dev/null 2>&1
  else
    return 1
  fi
}

if [ -f "$PID_FILE" ]; then
  EXISTING_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo "Existing backend process found. Restarting pid=$EXISTING_PID"
    "$ROOT_DIR/deploy/stop_backend.sh"
  else
    echo "Removing stale backend pid file. pid=${EXISTING_PID:-unknown}"
    rm -f "$PID_FILE"
  fi
fi

if command -v ss >/dev/null 2>&1 ||
   command -v netstat >/dev/null 2>&1 ||
   command -v lsof >/dev/null 2>&1 ||
   command -v fuser >/dev/null 2>&1; then
  if is_port_in_use; then
    echo "Backend port $BACKEND_PORT is already in use. Run deploy/stop_backend.sh first."
    exit 1
  fi
else
  echo "Port check skipped: no supported port inspection tool"
fi

cd "$BACKEND_DIR"
. .venv/bin/activate

echo "Backend CORS origins: ${CORS_ORIGINS:-<application defaults>}"
nohup python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" >> "$LOG_FILE" 2>&1 &
NEW_PID="$!"

attempt=1
while [ "$attempt" -le 15 ]; do
  sleep 1

  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    echo "Backend process exited during startup."
    tail -n 50 "$LOG_FILE" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
  fi

  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
    echo "$NEW_PID" > "$PID_FILE"
    echo "Backend started. pid=$NEW_PID, port=$BACKEND_PORT, log=$LOG_FILE"
    exit 0
  fi

  attempt=$((attempt + 1))
done

echo "Backend health check timed out."
tail -n 50 "$LOG_FILE" 2>/dev/null || true
kill "$NEW_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
