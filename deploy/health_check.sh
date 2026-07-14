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
LOG_FILE="$LOG_DIR/health_check.log"

mkdir -p "$LOG_DIR"

FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3010}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8001/health}"
BACKEND_DB_HEALTH_URL="${BACKEND_DB_HEALTH_URL:-http://127.0.0.1:8001/health/db}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"
DIST_INDEX="$ROOT_DIR/frontend/dist/index.html"

check_url() {
  label="$1"
  url="$2"
  if curl -fsS "$url" >/dev/null; then
    echo "OK  $label $url"
  else
    echo "FAIL $label $url"
    return 1
  fi
}

check_backend_pid() {
  pid_file="$LOG_DIR/backend.pid"
  if [ ! -f "$pid_file" ]; then
    echo "FAIL Backend PID file missing: $pid_file"
    return 1
  fi
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "OK  Backend PID running: $pid"
    return 0
  fi
  echo "FAIL Backend PID is not running: ${pid:-invalid}"
  return 1
}

check_openapi_path() {
  path="$1"
  openapi_url="http://127.0.0.1:$BACKEND_PORT/openapi.json"
  if curl -fsS "$openapi_url" | grep -F -q "\"$path\""; then
    echo "OK  OpenAPI path=$path"
    return 0
  fi
  echo "FAIL OpenAPI path missing: $path ($openapi_url)"
  echo "Backend process is not running the current application code."
  return 1
}

get_bundle() {
  sed -n 's/.*src="\/\(assets\/index-[^"]*\.js\)".*/\1/p' | head -n 1
}

check_env_origin() {
  origin="$1"
  if [ -f "$BACKEND_ENV_FILE" ] &&
     grep -F "CORS_ORIGINS=" "$BACKEND_ENV_FILE" | grep -F -q "$origin"; then
    echo "OK  backend/.env contains required origin: $origin"
  else
    echo "FAIL backend/.env missing required origin: $origin"
    return 1
  fi
}

check_cors_origin() {
  origin="$1"
  headers="$LOG_DIR/health-cors.$$.tmp"
  if ! curl -sSi -H "Origin: $origin" \
    "http://127.0.0.1:$BACKEND_PORT/network/status" > "$headers"; then
    echo "FAIL CORS request origin=$origin"
    rm -f "$headers"
    return 1
  fi
  if tr -d '\r' < "$headers" |
    grep -F -i -q "access-control-allow-origin: $origin"; then
    echo "OK  CORS origin=$origin"
    rm -f "$headers"
    return 0
  fi
  echo "FAIL CORS header missing origin=$origin"
  rm -f "$headers"
  return 1
}

check_frontend_bundle() {
  if [ ! -f "$DIST_INDEX" ]; then
    echo "FAIL Built frontend index missing: $DIST_INDEX"
    return 1
  fi
  built_bundle="$(get_bundle < "$DIST_INDEX")"
  served_bundle="$(curl -fsS "$FRONTEND_URL/" | get_bundle)"
  echo "Built frontend bundle:  $built_bundle"
  echo "Served frontend bundle: $served_bundle"
  if [ -n "$built_bundle" ] && [ "$built_bundle" = "$served_bundle" ]; then
    echo "OK  Frontend bundle matches"
  else
    echo "FAIL Frontend is not serving the current dist"
    echo "Frontend pid: $(cat "$LOG_DIR/frontend.pid" 2>/dev/null || echo missing)"
    echo "Frontend dist: $ROOT_DIR/frontend/dist"
    echo "Current commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    if command -v lsof >/dev/null 2>&1; then
      lsof -nP -iTCP:"${FRONTEND_PORT:-3010}" -sTCP:LISTEN 2>/dev/null || true
    elif command -v ss >/dev/null 2>&1; then
      ss -ltnp 2>/dev/null | grep ":${FRONTEND_PORT:-3010} " || true
    fi
    return 1
  fi
}

check_frontend_cache_headers() {
  headers="$LOG_DIR/frontend-cache.$$.tmp"
  if ! curl -sSI "$FRONTEND_URL/" > "$headers"; then
    echo "FAIL Cannot inspect frontend cache headers"
    rm -f "$headers"
    return 1
  fi
  if tr -d '\r' < "$headers" | grep -i -q '^Cache-Control:.*no-store'; then
    echo "OK  Frontend index cache disabled"
    rm -f "$headers"
    return 0
  fi
  echo "FAIL Frontend index.html is missing Cache-Control no-store"
  rm -f "$headers"
  return 1
}

run_checks() {
  date
  git -C "$ROOT_DIR" log -1 --oneline || return 1
  check_env_origin "http://192.168.222.210:3010" || return 1
  check_env_origin "http://112.216.230.162:3010" || return 1
  check_env_origin "http://thelimo.asuscomm.com:3010" || return 1
  check_env_origin "http://localhost:5173" || return 1
  check_env_origin "http://localhost:3010" || return 1
  check_url "Frontend" "$FRONTEND_URL" || return 1
  check_url "Backend" "$BACKEND_HEALTH_URL" || return 1
  check_url "Database" "$BACKEND_DB_HEALTH_URL" || return 1
  check_backend_pid || return 1
  check_url "OpenAPI" "http://127.0.0.1:$BACKEND_PORT/openapi.json" || return 1
  check_openapi_path "/hr/accounts" || return 1
  check_frontend_bundle || return 1
  check_frontend_cache_headers || return 1
  check_cors_origin "http://192.168.222.210:3010" || return 1
  check_cors_origin "http://112.216.230.162:3010" || return 1
}

TMP_LOG="$LOG_DIR/health-check.$$.tmp"
trap 'rm -f "$TMP_LOG"' EXIT

if run_checks > "$TMP_LOG" 2>&1; then
  CHECK_STATUS=0
else
  CHECK_STATUS=$?
fi

tee -a "$LOG_FILE" < "$TMP_LOG"
exit "$CHECK_STATUS"
