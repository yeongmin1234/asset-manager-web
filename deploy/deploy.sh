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
LOG_FILE="$LOG_DIR/deploy.log"

mkdir -p "$LOG_DIR"

{
  echo "== Asset Manager direct deploy =="
  date
  echo "Project: $ROOT_DIR"
  echo "Git update is not automated. Apply files manually before running this script."

  echo "== Backend dependency check =="
  cd "$ROOT_DIR/backend"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  pip install -r requirements.txt

  echo "== Frontend build =="
  cd "$ROOT_DIR/frontend"
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
  npm run build

  echo "== Restart services =="
  "$ROOT_DIR/deploy/stop_all.sh"
  "$ROOT_DIR/deploy/start_backend.sh"
  "$ROOT_DIR/deploy/start_frontend.sh"

  echo "== Health check =="
  "$ROOT_DIR/deploy/health_check.sh"
} 2>&1 | tee -a "$LOG_FILE"
