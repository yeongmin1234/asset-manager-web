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

stop_frontend_pid() {
  stop_target_pid="$1"
  frontend_pid_matches "$stop_target_pid" || return 1
  echo "Stopping verified asset-manager frontend. pid=$stop_target_pid"
  kill "$stop_target_pid" || return 1
  wait_count=0
  while kill -0 "$stop_target_pid" 2>/dev/null && [ "$wait_count" -lt 10 ]; do
    sleep 1
    wait_count=$((wait_count + 1))
  done
  if kill -0 "$stop_target_pid" 2>/dev/null && frontend_pid_matches "$stop_target_pid"; then
    kill -KILL "$stop_target_pid" || return 1
    sleep 1
  fi
  if kill -0 "$stop_target_pid" 2>/dev/null && frontend_pid_matches "$stop_target_pid"; then
    echo "Frontend process remains alive. pid=$stop_target_pid" >&2
    return 1
  fi
}

saved_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -n "$saved_pid" ] && ! frontend_pid_matches "$saved_pid"; then
  echo "Removing stale or unrelated frontend PID file. pid=$saved_pid"
  rm -f "$PID_FILE"
  saved_pid=""
fi
candidate_pids="$(printf '%s\n%s\n%s\n' "$saved_pid" "$(frontend_listener_pids)" "$(frontend_ps_pids)" |
  grep -E '^[0-9]+$' | sort -u || true)"
verified_pids=""
for candidate_pid in $candidate_pids; do
  if frontend_pid_matches "$candidate_pid"; then
    verified_pids="${verified_pids}${verified_pids:+ }$candidate_pid"
  fi
done
set -- $verified_pids
if [ "$#" -gt 1 ]; then
  echo "Multiple verified asset-manager frontends; refusing to stop any. pids=$verified_pids" >&2
  exit 1
fi
if [ "$#" -eq 1 ]; then
  stop_frontend_pid "$1" || exit 1
fi
rm -f "$PID_FILE"

remaining_pids=""
for candidate_pid in $(frontend_ps_pids); do
  if frontend_pid_matches "$candidate_pid"; then
    remaining_pids="${remaining_pids}${remaining_pids:+ }$candidate_pid"
  fi
done
if [ -n "$remaining_pids" ]; then
  echo "Verified frontend processes remain after stop. pids=$remaining_pids" >&2
  exit 1
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
