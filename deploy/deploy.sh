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
BUILD_LOG="$LOG_DIR/frontend-build.$$.tmp"
trap 'rm -f "$TMP_LOG" "$BUILD_LOG"' EXIT

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

run_frontend_build() {
  echo "Running frontend build."
  if npm run build > "$BUILD_LOG" 2>&1; then
    cat "$BUILD_LOG"
    echo "Frontend build completed."
    return 0
  fi

  echo "Frontend build failed."
  cat "$BUILD_LOG"

  if grep -E "@rollup/rollup-linux-x64-gnu|optional dependencies" "$BUILD_LOG" >/dev/null 2>&1; then
    echo "Rollup optional dependency issue detected."
    echo "Reinstalling frontend dependencies with optional packages."
    rm -rf node_modules || return 1
    npm install --include=optional || return 1

    echo "Retrying frontend build."
    if npm run build; then
      echo "Frontend build completed after Rollup optional dependency recovery."
      return 0
    fi

    echo "Frontend build retry failed."
    return 1
  fi

  echo "Frontend build failed for a non-Rollup optional dependency reason."
  return 1
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
  git pull --ff-only || return 1

  echo "== Database backup =="
  BACKUP_SCRIPT="$ROOT_DIR/deploy/backup_db.sh"
  if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "Database backup script not found: $BACKUP_SCRIPT"
    return 1
  fi
  if [ ! -x "$BACKUP_SCRIPT" ]; then
    echo "Database backup script is not executable: $BACKUP_SCRIPT"
    return 1
  fi
  echo "Starting database backup before migration."
  "$BACKUP_SCRIPT" || return 1
  echo "Database backup completed."

  echo "== Backend dependency check =="
  unset DATABASE_URL
  cd "$ROOT_DIR/backend"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv || return 1
  fi
  . .venv/bin/activate
  python -m pip install -r requirements.txt || return 1

  echo "== Backend compile check =="
  python -m compileall app || return 1

  echo "== Database migration =="
  alembic upgrade head || return 1
  alembic current || return 1

  echo "== Frontend build =="
  cd "$ROOT_DIR/frontend"
  if [ -f "package-lock.json" ]; then
    npm ci || return 1
  else
    npm install || return 1
  fi
  run_frontend_build || return 1

  echo "== Restart services =="
  "$ROOT_DIR/deploy/stop_all.sh" || return 1
  "$ROOT_DIR/deploy/start_backend.sh" || return 1
  "$ROOT_DIR/deploy/start_frontend.sh" || return 1

  echo "== Health check =="
  "$ROOT_DIR/deploy/health_check.sh" || return 1

  echo "== Direct endpoint check =="
  check_url "Backend health" "http://127.0.0.1:8010/health" || return 1
  check_url "Backend DB health" "http://127.0.0.1:8010/health/db" || return 1
  check_url "Software list" "http://127.0.0.1:8010/software" || return 1
  check_url "Software summary" "http://127.0.0.1:8010/software/summary" || return 1
  check_url "Frontend" "http://127.0.0.1:3010" || return 1
}

if run_deploy > "$TMP_LOG" 2>&1; then
  DEPLOY_STATUS=0
else
  DEPLOY_STATUS=$?
fi

tee -a "$LOG_FILE" < "$TMP_LOG"
exit "$DEPLOY_STATUS"
