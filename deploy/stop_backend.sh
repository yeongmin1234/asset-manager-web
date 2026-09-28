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

saved_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -n "$saved_pid" ] && ! backend_pid_matches "$saved_pid"; then
  echo "Removing stale or unrelated backend PID file. pid=$saved_pid"
  rm -f "$PID_FILE"
  saved_pid=""
fi

# Listener tools can omit PID on Synology. Collect the PID file, listener tools,
# and ps candidates, then verify every candidate against the exact command.
candidate_pids="$(printf '%s\n%s\n%s\n' "$saved_pid" "$(backend_listener_pids)" "$(backend_ps_pids)" |
  grep -E '^[0-9]+$' | sort -u || true)"
verified_pids=""
for candidate_pid in $candidate_pids; do
  if backend_pid_matches "$candidate_pid"; then
    verified_pids="${verified_pids}${verified_pids:+ }$candidate_pid"
  fi
done
set -- $verified_pids
if [ "$#" -gt 1 ]; then
  echo "Multiple verified asset-manager backends; refusing to stop any. pids=$verified_pids" >&2
  exit 1
fi
if [ "$#" -eq 1 ]; then
  stop_backend_pid "$1" || exit 1
fi
rm -f "$PID_FILE"

remaining_pids=""
for candidate_pid in $(backend_ps_pids); do
  if backend_pid_matches "$candidate_pid"; then
    remaining_pids="${remaining_pids}${remaining_pids:+ }$candidate_pid"
  fi
done
if [ -n "$remaining_pids" ]; then
  echo "Verified backend processes remain after stop. pids=$remaining_pids" >&2
  exit 1
fi

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
