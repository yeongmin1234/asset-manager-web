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

get_frontend_bundle() {
  index_file="$1"
  sed -n 's/.*src="\/\(assets\/index-[^"]*\.js\)".*/\1/p' "$index_file" | head -n 1
}

verify_frontend_bundle() {
  frontend_port="${FRONTEND_PORT:-3010}"
  expected_index="$ROOT_DIR/frontend/dist/index.html"
  expected_bundle="$(get_frontend_bundle "$expected_index")"
  if [ -z "$expected_bundle" ]; then
    echo "Cannot find built frontend JS bundle in $expected_index"
    return 1
  fi

  served_index="$LOG_DIR/frontend-served-index.$$.html"
  served_url="http://127.0.0.1:$frontend_port/"
  if ! curl -fsS -H "Cache-Control: no-cache" "$served_url" > "$served_index"; then
    echo "Cannot fetch served frontend index from $served_url"
    rm -f "$served_index"
    return 1
  fi

  served_bundle="$(get_frontend_bundle "$served_index")"
  echo "Built frontend bundle:  $expected_bundle"
  echo "Served frontend bundle: $served_bundle"

  if grep -q "$expected_bundle" "$served_index"; then
    echo "OK  Frontend served bundle $expected_bundle"
    rm -f "$served_index"
    return 0
  fi

  echo "FAIL Frontend served index does not reference built bundle $expected_bundle"
  rm -f "$served_index"
  return 1
}

restore_package_lock_if_only_dirty() {
  reason="$1"
  current_dir="$(pwd)"
  cd "$ROOT_DIR"

  status="$(git status --porcelain)"
  if [ -z "$status" ]; then
    cd "$current_dir"
    return 0
  fi

  other_changes="$(printf '%s\n' "$status" | grep -v '^.. frontend/package-lock\.json$' || true)"
  if [ -n "$other_changes" ]; then
    echo "Working tree is dirty. Commit, stash, or remove local changes before deploy."
    echo "Changed files:"
    git status --short
    cd "$current_dir"
    return 1
  fi

  echo "$reason"
  echo "Only frontend/package-lock.json changed. Restoring it before continuing."
  git restore -- frontend/package-lock.json || {
    cd "$current_dir"
    return 1
  }

  if [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is still dirty after restoring frontend/package-lock.json."
    echo "Changed files:"
    git status --short
    cd "$current_dir"
    return 1
  fi

  cd "$current_dir"
  return 0
}

run_frontend_build() {
  echo "Running frontend build."
  if npm run build > "$BUILD_LOG" 2>&1; then
    cat "$BUILD_LOG"
    echo "Frontend build completed."
    restore_package_lock_if_only_dirty "Checking for package-lock changes after frontend build." || return 1
    return 0
  fi

  echo "Frontend build failed."
  cat "$BUILD_LOG"

  if grep -E "@rollup/rollup-linux-x64-gnu|optional dependencies|removing both package-lock.json and node_modules" "$BUILD_LOG" >/dev/null 2>&1; then
    echo "Rollup optional dependency issue detected."
    echo "Removing node_modules and package-lock.json for Rollup optional dependency recovery."
    rm -rf node_modules package-lock.json || return 1
    echo "Reinstalling frontend dependencies with optional packages."
    npm install --include=optional || {
      restore_package_lock_if_only_dirty "Cleaning package-lock change after failed optional dependency install." || return 1
      return 1
    }
    echo "Installing Rollup Linux optional package explicitly."
    npm install --no-save @rollup/rollup-linux-x64-gnu || {
      restore_package_lock_if_only_dirty "Cleaning package-lock change after failed Rollup optional package install." || return 1
      return 1
    }

    echo "Retrying frontend build."
    if npm run build; then
      echo "Frontend build completed after Rollup optional dependency recovery."
      restore_package_lock_if_only_dirty "Checking for package-lock changes after Rollup optional dependency recovery." || return 1
      return 0
    fi

    echo "Frontend build retry failed."
    restore_package_lock_if_only_dirty "Cleaning package-lock change after failed Rollup recovery build." || return 1
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
  restore_package_lock_if_only_dirty "Checking working tree before deploy." || return 1
  git pull --ff-only || return 1
  echo "Current commit:"
  git log -1 --oneline || return 1

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
  echo "Built frontend bundle:"
  get_frontend_bundle "$ROOT_DIR/frontend/dist/index.html" || return 1

  echo "== Restart services =="
  "$ROOT_DIR/deploy/stop_all.sh" || return 1
  "$ROOT_DIR/deploy/start_backend.sh" || return 1
  "$ROOT_DIR/deploy/start_frontend.sh" || return 1

  echo "== Health check =="
  "$ROOT_DIR/deploy/health_check.sh" || return 1
  verify_frontend_bundle || return 1

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
