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
PID_FILE="$ROOT_DIR/logs/backend.pid"
BACKEND_PORT="${BACKEND_PORT:-${PORT:-8010}}"
. "$ROOT_DIR/deploy/backend_process.sh"

stop_backend_pid() {
  stop_target_pid="$1"
  backend_pid_matches "$stop_target_pid" || return 1
  echo "Stopping verified asset-manager backend. pid=$stop_target_pid"
  kill "$stop_target_pid" || return 1
  stop_wait=0
  while kill -0 "$stop_target_pid" 2>/dev/null && [ "$stop_wait" -lt 10 ]; do
    sleep 1
    stop_wait=$((stop_wait + 1))
  done
  if kill -0 "$stop_target_pid" 2>/dev/null; then
    if backend_pid_matches "$stop_target_pid"; then
      echo "Force stopping verified asset-manager backend. pid=$stop_target_pid"
      kill -KILL "$stop_target_pid" || return 1
      sleep 1
    fi
  fi
  if kill -0 "$stop_target_pid" 2>/dev/null && backend_pid_matches "$stop_target_pid"; then
    echo "Backend process remains alive. pid=$stop_target_pid" >&2
    return 1
  fi
  return 0
}

if [ -f "$PID_FILE" ]; then
  saved_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if backend_pid_matches "$saved_pid"; then
    stop_backend_pid "$saved_pid" || exit 1
  else
    echo "Ignoring stale or unrelated backend PID file. pid=${saved_pid:-missing}"
  fi
  rm -f "$PID_FILE"
else
  echo "Backend PID file not found; checking port $BACKEND_PORT."
fi

# Docker is not part of direct deploy. Never stop a container based on port alone.
listener_pids="$(backend_listener_pids | sort -u)"
for listener_pid in $listener_pids; do
  if backend_pid_matches "$listener_pid"; then
    stop_backend_pid "$listener_pid" || exit 1
  else
    echo "Leaving unrelated or unverifiable port $BACKEND_PORT listener alone. pid=$listener_pid"
  fi
done

if backend_port_status; then
  echo "Backend port $BACKEND_PORT is still in use; refusing to report a successful stop." >&2
  exit 1
else
  port_result=$?
  if [ "$port_result" -ne 1 ]; then
    echo "Cannot verify that backend port $BACKEND_PORT is free." >&2
    exit 1
  fi
fi

echo "Backend stopped. port=$BACKEND_PORT"
