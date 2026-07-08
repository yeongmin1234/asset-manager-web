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

is_pid_running() {
  pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
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

is_port_in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | grep -q ":$FRONTEND_PORT "
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn | grep -q ":$FRONTEND_PORT "
  elif command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$FRONTEND_PORT" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v fuser >/dev/null 2>&1; then
    fuser "$FRONTEND_PORT/tcp" >/dev/null 2>&1
  else
    return 1
  fi
}

stop_frontend_port_owners() {
  if ! is_port_in_use; then
    return 0
  fi

  echo "Frontend port $FRONTEND_PORT is already in use. Cleaning existing listener before start."

  if command -v docker >/dev/null 2>&1; then
    docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' |
      grep -E "(:|\\[::\\]:)$FRONTEND_PORT->" |
      while read -r container_id container_name container_ports; do
        echo "Stopping Docker container on frontend port $FRONTEND_PORT: $container_name ($container_id)"
        docker stop "$container_id" >/dev/null || true
      done
    sleep 1
  fi

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"$FRONTEND_PORT" -sTCP:LISTEN 2>/dev/null || true)"
    for pid in $pids; do
      stop_pid "$pid" "frontend port $FRONTEND_PORT listener"
    done
  elif command -v fuser >/dev/null 2>&1; then
    echo "Stopping processes with fuser on $FRONTEND_PORT/tcp"
    fuser -k "$FRONTEND_PORT/tcp" 2>/dev/null || true
    sleep 1
  else
    echo "Cannot identify port $FRONTEND_PORT owner: lsof/fuser not found."
  fi

  if is_port_in_use; then
    echo "Frontend port $FRONTEND_PORT is still in use after cleanup."
    echo "Check with: sudo lsof -i :$FRONTEND_PORT"
    exit 1
  fi
}

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if is_pid_running "$PID"; then
    stop_pid "$PID" "frontend pid file process"
  else
    echo "Removing stale frontend pid file. pid=$PID"
  fi
  rm -f "$PID_FILE"
fi

stop_frontend_port_owners

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
