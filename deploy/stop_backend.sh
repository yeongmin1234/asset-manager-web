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

is_pid_running() {
  pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

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

find_backend_processes() {
  ps 2>/dev/null | awk -v port="$BACKEND_PORT" '
    /[u]vicorn/ && /app\.main:app/ {
      for (index = 1; index <= NF; index += 1) {
        if ($index == "--port" && $(index + 1) == port) {
          print $1
        }
      }
    }
  '
}

stop_pid() {
  pid="$1"
  label="$2"
  if ! is_pid_running "$pid"; then
    return 0
  fi
  echo "Stopping $label. pid=$pid"
  kill "$pid" 2>/dev/null || true
  count=0
  while is_pid_running "$pid" && [ "$count" -lt 10 ]; do
    sleep 1
    count=$((count + 1))
  done
  if is_pid_running "$pid"; then
    echo "Force stopping $label. pid=$pid"
    kill -KILL "$pid" 2>/dev/null || true
  fi
}

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  stop_pid "$PID" "backend pid file process"
  rm -f "$PID_FILE"
else
  echo "Backend pid file not found; checking port $BACKEND_PORT."
fi

if command -v docker >/dev/null 2>&1; then
  docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' |
    grep -E "(:|\\[::\\]:)$BACKEND_PORT->" |
    while read -r container_id container_name container_ports; do
      echo "Stopping Docker container on backend port $BACKEND_PORT: $container_name ($container_id)"
      docker stop "$container_id" >/dev/null || true
    done
fi

if command -v lsof >/dev/null 2>&1; then
  pids="$(lsof -ti tcp:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null || true)"
  for pid in $pids; do
    stop_pid "$pid" "backend port $BACKEND_PORT listener"
  done
elif command -v fuser >/dev/null 2>&1; then
  if fuser "$BACKEND_PORT/tcp" >/dev/null 2>&1; then
    echo "Stopping processes with fuser on $BACKEND_PORT/tcp"
    fuser -k "$BACKEND_PORT/tcp" 2>/dev/null || true
  fi
fi

pids="$(find_backend_processes || true)"
for pid in $pids; do
  stop_pid "$pid" "uvicorn app.main:app port $BACKEND_PORT process"
done

if is_port_in_use; then
  echo "Backend port $BACKEND_PORT is still in use; refusing to report a successful stop."
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep ":$BACKEND_PORT " || true
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltnp 2>/dev/null | grep ":$BACKEND_PORT " || true
  fi
  exit 1
fi

echo "Backend stopped. port=$BACKEND_PORT"
