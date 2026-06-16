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
TMP_LOG="$LOG_DIR/deploy.$$.tmp"
trap 'rm -f "$TMP_LOG"' EXIT

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

run_deploy() {
  echo "== Asset Manager direct deploy =="
  date
  echo "Project: $ROOT_DIR"

  echo "== Git update =="
  cd "$ROOT_DIR"
  git status --short
  if [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is dirty. Commit, stash, or remove local changes before deploy."
    echo "Changed files:"
    git status --short
    return 1
  fi
  git pull --ff-only

  echo "== Backend dependency check =="
  cd "$ROOT_DIR/backend"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  python -m pip install -r requirements.txt

  echo "== Backend compile check =="
  python -m compileall app

  echo "== Database migration =="
  alembic upgrade head
  alembic current

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

  echo "== Direct endpoint check =="
  check_url "Backend health" "http://127.0.0.1:8010/health"
  check_url "Backend DB health" "http://127.0.0.1:8010/health/db"
  check_url "Software list" "http://127.0.0.1:8010/software"
  check_url "Software summary" "http://127.0.0.1:8010/software/summary"
  check_url "Frontend" "http://127.0.0.1:3010"
}

if run_deploy > "$TMP_LOG" 2>&1; then
  DEPLOY_STATUS=0
else
  DEPLOY_STATUS=$?
fi

tee -a "$LOG_FILE" < "$TMP_LOG"
exit "$DEPLOY_STATUS"
