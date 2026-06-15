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

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Backend is already running. pid=$(cat "$PID_FILE")"
  exit 0
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Backend venv not found: $BACKEND_DIR/.venv"
  echo "Create it first: cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

BACKEND_HOST="${BACKEND_HOST:-${HOST:-0.0.0.0}}"
BACKEND_PORT="${BACKEND_PORT:-${PORT:-8001}}"

cd "$BACKEND_DIR"
. .venv/bin/activate

nohup python -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" >> "$LOG_FILE" 2>&1 &
echo "$!" > "$PID_FILE"
echo "Backend started. pid=$(cat "$PID_FILE"), port=$BACKEND_PORT, log=$LOG_FILE"
