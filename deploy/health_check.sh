#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/health_check.log"
ENV_FILE="${ASSET_MANAGER_ENV:-$ROOT_DIR/deploy/.env}"

mkdir -p "$LOG_DIR"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3010}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8001/health}"
BACKEND_DB_HEALTH_URL="${BACKEND_DB_HEALTH_URL:-http://127.0.0.1:8001/health/db}"

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

{
  date
  check_url "Frontend" "$FRONTEND_URL"
  check_url "Backend" "$BACKEND_HEALTH_URL"
  check_url "Database" "$BACKEND_DB_HEALTH_URL"
} 2>&1 | tee -a "$LOG_FILE"
