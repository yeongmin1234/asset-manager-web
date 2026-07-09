#!/usr/bin/env sh
set -eu

DEPLOY_MODE="pull"
case "${1:-}" in
  "")
    ;;
  --no-pull)
    DEPLOY_MODE="no-pull"
    ;;
  --check)
    DEPLOY_MODE="check"
    ;;
  *)
    echo "Usage: $0 [--no-pull|--check]"
    exit 2
    ;;
esac

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
PULL_LOG="$LOG_DIR/git-pull.$$.tmp"
trap 'rm -f "$TMP_LOG" "$BUILD_LOG" "$PULL_LOG"' EXIT

show_port_owner() {
  port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep ":$port " || true
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltnp 2>/dev/null | grep ":$port " || true
  else
    echo "Port owner tools unavailable (lsof/ss/netstat)."
  fi
}

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

check_cors_origin() {
  origin="$1"
  url="http://127.0.0.1:${BACKEND_PORT:-8010}/network/status"
  headers="$LOG_DIR/cors-headers.$$.tmp"
  if ! curl -sSi -H "Origin: $origin" "$url" > "$headers"; then
    echo "FAIL CORS request origin=$origin url=$url"
    rm -f "$headers"
    return 1
  fi
  if tr -d '\r' < "$headers" | grep -i -q "^access-control-allow-origin: $origin$"; then
    echo "OK  CORS origin=$origin"
    rm -f "$headers"
    return 0
  fi
  echo "FAIL Missing access-control-allow-origin for $origin"
  cat "$headers"
  rm -f "$headers"
  return 1
}

get_frontend_bundle() {
  index_file="$1"
  sed -n 's/.*src="\/\(assets\/index-[^"]*\.js\)".*/\1/p' "$index_file" | head -n 1
}

validate_project_root() {
  if [ ! -f "$ROOT_DIR/frontend/package.json" ] ||
     [ ! -f "$ROOT_DIR/backend/app/main.py" ]; then
    echo "FAIL Invalid project root: $ROOT_DIR"
    return 1
  fi
}

print_checkout_status() {
  echo "Project: $ROOT_DIR"
  echo "Current commit:"
  git -C "$ROOT_DIR" log -1 --oneline || return 1
  echo "Git status:"
  git -C "$ROOT_DIR" status --short || return 1
}

ensure_tracked_checkout_clean() {
  tracked_status="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=no)"
  if [ -n "$tracked_status" ]; then
    echo "FAIL Tracked files have local changes; deployment will not overwrite them."
    printf '%s\n' "$tracked_status"
    echo "Commit or stash the changes, then retry."
    return 1
  fi
}

pull_checkout() {
  echo "== Git pull --ff-only =="
  if git -C "$ROOT_DIR" pull --ff-only > "$PULL_LOG" 2>&1; then
    cat "$PULL_LOG"
    echo "OK  Git pull completed."
    return 0
  fi

  cat "$PULL_LOG"
  echo "FAIL git pull --ff-only; deployment stopped before build/restart."
  if grep -E -i "authentication|could not read Username|terminal prompts disabled|permission denied|403|401" "$PULL_LOG" >/dev/null 2>&1; then
    echo "Cause hint: GitHub authentication is unavailable for the current user/sudo environment."
  elif grep -E -i "local changes|would be overwritten|not possible to fast-forward|divergent|conflict" "$PULL_LOG" >/dev/null 2>&1; then
    echo "Cause hint: local changes or branch divergence prevent a safe fast-forward pull."
  else
    echo "Cause hint: inspect the Git output above (network, remote, authentication, or branch state)."
  fi
  echo "No reset, checkout, merge, build, or service restart was performed."
  return 1
}

run_check_mode() {
  echo "== Asset Manager deployment check =="
  date
  validate_project_root || return 1
  print_checkout_status || return 1
  echo "Deploy mode: check only (no pull/build/restart)"
  echo "Port status:"
  "$ROOT_DIR/deploy/check_ports.sh" || true
  echo "Port 3010 owner:"
  show_port_owner 3010
  echo "Port 8010 owner:"
  show_port_owner 8010

  index_file="$ROOT_DIR/frontend/dist/index.html"
  if [ -f "$index_file" ]; then
    built_bundle="$(get_frontend_bundle "$index_file")"
  else
    built_bundle=""
  fi
  served_bundle="$(curl -fsS "http://127.0.0.1:${FRONTEND_PORT:-3010}/" 2>/dev/null | get_bundle_from_stdin || true)"
  echo "Built frontend bundle:  ${built_bundle:-missing}"
  echo "Served frontend bundle: ${served_bundle:-unavailable}"
  echo "Frontend dist: $ROOT_DIR/frontend/dist"
}

get_bundle_from_stdin() {
  sed -n 's/.*src="\/\(assets\/index-[^"]*\.js\)".*/\1/p' | head -n 1
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

  if [ -n "$served_bundle" ] && [ "$expected_bundle" = "$served_bundle" ]; then
    echo "OK  Frontend served bundle $expected_bundle"
    rm -f "$served_index"
    return 0
  fi

  echo "FAIL Frontend served index does not reference built bundle $expected_bundle"
  echo "Frontend pid: $(cat "$LOG_DIR/frontend.pid" 2>/dev/null || echo missing)"
  echo "Frontend dist: $ROOT_DIR/frontend/dist"
  echo "Current commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "Port ${FRONTEND_PORT:-3010} owner:"
  show_port_owner "${FRONTEND_PORT:-3010}"
  rm -f "$served_index"
  return 1
}

check_frontend_artifacts() {
  dist_dir="$ROOT_DIR/frontend/dist"
  index_file="$dist_dir/index.html"
  if [ ! -f "$index_file" ]; then
    echo "FAIL Missing frontend build index: $index_file"
    return 1
  fi

  bundle="$(get_frontend_bundle "$index_file")"
  if [ -z "$bundle" ] || [ ! -f "$dist_dir/$bundle" ]; then
    echo "FAIL Missing frontend JS bundle referenced by $index_file: $bundle"
    return 1
  fi

  if grep -R -E "BALMUDA|app-splash|너의 목소리" "$dist_dir" >/dev/null 2>&1; then
    echo "FAIL Removed intro content remains in frontend/dist."
    grep -R -l -E "BALMUDA|app-splash|너의 목소리" "$dist_dir" || true
    return 1
  fi

  if grep -R -F "192.168.222.210:8010" "$dist_dir" >/dev/null 2>&1; then
    echo "FAIL Fixed internal API URL remains in frontend/dist."
    grep -R -l -F "192.168.222.210:8010" "$dist_dir" || true
    return 1
  fi

  if grep -R -F "http://192.168.222.210" "$dist_dir" >/dev/null 2>&1; then
    echo "FAIL Fixed internal API host remains in frontend/dist."
    grep -R -l -F "http://192.168.222.210" "$dist_dir" || true
    return 1
  fi

  echo "OK  Frontend artifact checks"
  echo "Built frontend bundle: $bundle"
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

  echo "== Current checkout =="
  cd "$ROOT_DIR"
  validate_project_root || return 1
  print_checkout_status || return 1
  ensure_tracked_checkout_clean || return 1
  if [ "$DEPLOY_MODE" = "pull" ]; then
    pull_checkout || return 1
    echo "Checkout after pull:"
    git log -1 --oneline || return 1
    git status --short || return 1
  else
    echo "Git pull skipped by --no-pull; deploying the current checkout."
  fi

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

  echo "== Frontend build =="
  cd "$ROOT_DIR/frontend"
  if [ -f "package-lock.json" ]; then
    npm ci || return 1
  else
    npm install || return 1
  fi
  dist_dir="$ROOT_DIR/frontend/dist"
  if [ "$dist_dir" != "$ROOT_DIR/frontend/dist" ]; then
    echo "FAIL Unsafe frontend dist path: $dist_dir"
    return 1
  fi
  echo "Removing previous frontend dist: $dist_dir"
  rm -rf -- "$dist_dir" || return 1
  run_frontend_build || return 1
  check_frontend_artifacts || return 1

  echo "== Restart services =="
  "$ROOT_DIR/deploy/stop_all.sh" || return 1
  "$ROOT_DIR/deploy/start_backend.sh" || return 1
  "$ROOT_DIR/deploy/start_frontend.sh" || return 1

  echo "== Health check =="
  "$ROOT_DIR/deploy/health_check.sh" || return 1
  check_cors_origin "http://192.168.222.210:3010" || return 1
  check_cors_origin "http://112.216.230.162:3010" || return 1
  verify_frontend_bundle || return 1

  echo "== Direct endpoint check =="
  check_url "Backend health" "http://127.0.0.1:8010/health" || return 1
  check_url "Backend DB health" "http://127.0.0.1:8010/health/db" || return 1
  check_url "Frontend" "http://127.0.0.1:3010" || return 1
  echo "== Deployment complete =="
  echo "Frontend: http://127.0.0.1:3010"
  echo "Backend:  http://127.0.0.1:8010"
}

if [ "$DEPLOY_MODE" = "check" ]; then
  if run_check_mode > "$TMP_LOG" 2>&1; then
    DEPLOY_STATUS=0
  else
    DEPLOY_STATUS=$?
  fi
elif run_deploy > "$TMP_LOG" 2>&1; then
  DEPLOY_STATUS=0
else
  DEPLOY_STATUS=$?
fi

tee -a "$LOG_FILE" < "$TMP_LOG"
exit "$DEPLOY_STATUS"
