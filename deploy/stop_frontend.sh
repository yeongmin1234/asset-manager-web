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
FRONTEND_PORT="${FRONTEND_PORT:-3010}"
PID_FILE="$ROOT_DIR/logs/frontend.pid"
. "$ROOT_DIR/deploy/frontend_process.sh"

if [ -f "$PID_FILE" ]; then
  frontend_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if frontend_pid_matches "$frontend_pid"; then
    echo "Stopping verified asset-manager frontend. pid=$frontend_pid"
    kill "$frontend_pid" || exit 1
    wait_count=0
    while kill -0 "$frontend_pid" 2>/dev/null && [ "$wait_count" -lt 10 ]; do
      sleep 1
      wait_count=$((wait_count + 1))
    done
    if kill -0 "$frontend_pid" 2>/dev/null && frontend_pid_matches "$frontend_pid"; then
      kill -KILL "$frontend_pid" || exit 1
      sleep 1
    fi
    if kill -0 "$frontend_pid" 2>/dev/null && frontend_pid_matches "$frontend_pid"; then
      echo "Frontend process remains alive. pid=$frontend_pid" >&2
      exit 1
    fi
  else
    echo "Ignoring stale or unrelated frontend PID file. pid=${frontend_pid:-missing}"
  fi
  rm -f "$PID_FILE"
else
  echo "Frontend PID file not found; checking port $FRONTEND_PORT."
fi

if frontend_port_status; then
  echo "Frontend port $FRONTEND_PORT is still in use; no unrelated listener was stopped." >&2
  exit 1
else
  port_result=$?
  if [ "$port_result" -ne 1 ]; then
    echo "Cannot verify that frontend port $FRONTEND_PORT is free." >&2
    exit 1
  fi
fi

echo "Frontend stopped. port=$FRONTEND_PORT"
