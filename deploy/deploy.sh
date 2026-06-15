#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/deploy.log"

mkdir -p "$LOG_DIR"

{
  echo "== Asset Manager direct deploy =="
  date
  echo "Project: $ROOT_DIR"
  echo "Git update is intentionally not automated. Apply files before running this script."

  echo "== Backend dependency check =="
  cd "$ROOT_DIR/backend"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  pip install -r requirements.txt

  echo "== Frontend build =="
  cd "$ROOT_DIR/frontend"
  npm install
  npm run build

  echo "== Restart services =="
  "$ROOT_DIR/deploy/stop_all.sh"
  "$ROOT_DIR/deploy/start_all.sh"

  echo "== Health check =="
  "$ROOT_DIR/deploy/health_check.sh"
} 2>&1 | tee -a "$LOG_FILE"
