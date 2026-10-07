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
unset MIGRATION_DATABASE_URL

ROOT_DIR="${NAS_PROJECT_DIR:-$DEFAULT_ROOT_DIR}"
FRONTEND_SMOKE_NODE="${FRONTEND_SMOKE_NODE:-node}"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/deploy.log"

mkdir -p "$LOG_DIR"
TMP_LOG="$LOG_DIR/deploy.$$.tmp"
BUILD_LOG="$LOG_DIR/frontend-build.$$.tmp"
PULL_LOG="$LOG_DIR/git-pull.$$.tmp"
CANDIDATE_DIST=""
CANDIDATE_CREATED=false
PREVIOUS_DIST=""
DEPLOY_STAGE="PRECHECK"
DEPLOY_REASON="See the failed stage in the deploy log."
BROWSER_SMOKE_STATUS="NOT RUN"
BROWSER_SMOKE_AVAILABLE=false
trap 'rm -f "$TMP_LOG" "$BUILD_LOG" "$PULL_LOG"; if [ "$CANDIDATE_CREATED" = true ] && [ -d "$CANDIDATE_DIST" ]; then rm -rf -- "$CANDIDATE_DIST"; fi' EXIT

git_status_without_generated_dist() {
  # Exclude only this invocation's temporary directories, after the initial clean check.
  set -- .
  if [ -n "$CANDIDATE_DIST" ]; then
    set -- "$@" ":(exclude,literal)frontend/dist.next.$$"
  fi
  if [ -n "$PREVIOUS_DIST" ]; then
    set -- "$@" ":(exclude,literal)frontend/dist.previous.$$"
  fi
  git -C "$ROOT_DIR" status --porcelain --untracked-files=all -- "$@"
}

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

check_http_200() {
  label="$1"
  url="$2"
  status="$(curl --max-time 3 -sS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  if [ "$status" = "200" ]; then
    echo "OK  $label $url (200)"
    return 0
  fi
  echo "FAIL $label $url (HTTP ${status:-unreachable})"
  return 1
}

check_current_backend() {
  check_backend_pid_running || return 1
  check_http_200 "Backend health" "http://127.0.0.1:${BACKEND_PORT:-8010}/health" || return 1
  check_http_200 "Backend DB" "http://127.0.0.1:${BACKEND_PORT:-8010}/health/db" || return 1
  openapi_file="$LOG_DIR/backend-openapi.$$.tmp"
  if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT:-8010}/openapi.json" > "$openapi_file"; then
    rm -f "$openapi_file"
    echo "FAIL Backend OpenAPI is unavailable."
    return 1
  fi
  required_path="${REQUIRED_OPENAPI_PATH:-/online/recall/applications/preview}"
  if ! grep -F -q "\"$required_path\"" "$openapi_file"; then
    rm -f "$openapi_file"
    echo "FAIL Backend OpenAPI route missing: $required_path"
    return 1
  fi
  rm -f "$openapi_file"
  echo "OK  Backend OpenAPI route: $required_path"
}

rollback_frontend() {
  echo "Frontend deployment failed. Restoring the previous frontend."
  if ! "$ROOT_DIR/deploy/stop_frontend.sh"; then
    echo "FAIL Cannot stop the new frontend; manual recovery may be needed."
    return 1
  fi
  if [ -d "$PREVIOUS_DIST" ]; then
    if [ -d "$ROOT_DIR/frontend/dist" ]; then
      CANDIDATE_DIST="$ROOT_DIR/frontend/dist.next.$$"
      mv -- "$ROOT_DIR/frontend/dist" "$CANDIDATE_DIST" || return 1
      CANDIDATE_CREATED=true
    fi
    mv -- "$PREVIOUS_DIST" "$ROOT_DIR/frontend/dist" || return 1
    PREVIOUS_DIST=""
    "$ROOT_DIR/deploy/start_frontend.sh" || return 1
    check_http_200 "Restored frontend" "http://127.0.0.1:${FRONTEND_PORT:-3010}/" || return 1
    if [ "$BROWSER_SMOKE_AVAILABLE" = true ]; then
      run_frontend_browser_smoke || return 1
    fi
    echo "Previous frontend restored successfully."
  else
    echo "Previous frontend dist is unavailable; cannot restart it."
    return 1
  fi
}

rollback_frontend_or_report() {
  if ! rollback_frontend; then
    echo "CRITICAL: Frontend rollback failed."
    DEPLOY_REASON="$DEPLOY_REASON Previous frontend rollback also failed."
  fi
}

run_frontend_browser_smoke() {
  "$FRONTEND_SMOKE_NODE" "$ROOT_DIR/deploy/frontend_smoke_test.mjs" --url "${FRONTEND_SMOKE_URL:-http://127.0.0.1:${FRONTEND_PORT:-3010}/}"
}

check_frontend_browser_availability() {
  browser_log="$LOG_DIR/frontend-browser-precheck.$$.tmp"
  if "$FRONTEND_SMOKE_NODE" "$ROOT_DIR/deploy/frontend_smoke_test.mjs" --check-browser > "$browser_log" 2>&1; then
    cat "$browser_log"
    rm -f "$browser_log"
    BROWSER_SMOKE_AVAILABLE=true
    return 0
  else
    browser_status=$?
  fi
  if [ "$browser_status" -eq 2 ]; then
    echo "WARNING Browser smoke test skipped: Chromium/Chrome is not installed on this NAS."
    BROWSER_SMOKE_STATUS="SKIPPED (browser unavailable)"
    rm -f "$browser_log"
    return 0
  fi
  cat "$browser_log"
  rm -f "$browser_log"
  BROWSER_SMOKE_STATUS="FAIL"
  echo "FAIL Headless browser precheck failed for a reason other than a missing executable."
  return 1
}

report_deploy_result() {
  echo "========================================"
  if [ "$DEPLOY_STATUS" -eq 0 ]; then
    echo "DEPLOY SUCCESS"
    echo "Commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "Backend PID: $(cat "$LOG_DIR/backend.pid" 2>/dev/null || echo missing)"
    echo "Backend ${BACKEND_PORT:-8010}: OK"
    echo "Frontend PID: $(cat "$LOG_DIR/frontend.pid" 2>/dev/null || echo missing)"
    echo "Frontend ${FRONTEND_PORT:-3010}: OK"
    echo "Browser Smoke Test: $BROWSER_SMOKE_STATUS"
    echo "Database: OK"
    echo "Frontend bundle: $(get_frontend_bundle "$ROOT_DIR/frontend/dist/index.html")"
  else
    echo "DEPLOY FAILED"
    echo "Stage: $DEPLOY_STAGE"
    echo "Reason: $DEPLOY_REASON"
    echo "Browser Smoke Test: $BROWSER_SMOKE_STATUS"
    if check_http_200 "Current frontend" "http://127.0.0.1:${FRONTEND_PORT:-3010}/"; then
      echo "Current frontend: RUNNING"
    else
      echo "Current frontend: STOPPED/UNREACHABLE"
    fi
    if check_http_200 "Current backend" "http://127.0.0.1:${BACKEND_PORT:-8010}/health"; then
      echo "Current backend: RUNNING"
    else
      echo "Current backend: STOPPED/UNREACHABLE"
    fi
  fi
  echo "========================================"
}

show_backend_failure() {
  stage="$1"
  pid="$(cat "$LOG_DIR/backend.pid" 2>/dev/null || echo missing)"
  if health_status="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${BACKEND_PORT:-8010}/health" 2>/dev/null)"; then
    :
  else
    health_status="unreachable"
  fi
  echo "FAIL stage=$stage"
  echo "Backend PID: $pid"
  echo "Backend health status: $health_status"
  echo "Recent backend.log:"
  tail -n 80 "$LOG_DIR/backend.log" 2>/dev/null || echo "backend.log unavailable"
}

check_backend_pid_running() {
  pid="$(cat "$LOG_DIR/backend.pid" 2>/dev/null || true)"
  . "$ROOT_DIR/deploy/backend_process.sh"
  BACKEND_PORT="${BACKEND_PORT:-8010}"
  if [ -n "$pid" ] && backend_pid_matches "$pid" && kill -0 "$pid" 2>/dev/null; then
    echo "OK  Backend PID running: $pid"
    return 0
  fi
  echo "FAIL Backend PID is not running: ${pid:-missing}"
  return 1
}

verify_backend_stability() {
  label="$1"
  check_backend_pid_running || return 1
  check_url "$label" "http://127.0.0.1:${BACKEND_PORT:-8010}/health" || return 1
  echo "Waiting 10 seconds to confirm backend process stability."
  sleep 10
  check_backend_pid_running || return 1
  check_url "$label after 10s" "http://127.0.0.1:${BACKEND_PORT:-8010}/health" || return 1
}

start_backend_once() {
  if ! "$ROOT_DIR/deploy/start_backend.sh"; then
    show_backend_failure "backend start"
    return 1
  fi
  if ! verify_backend_stability "Backend health after start"; then
    show_backend_failure "backend stability"
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

get_frontend_css() {
  index_file="$1"
  sed -n 's/.*href="\/\(assets\/index-[^"]*\.css\)".*/\1/p' "$index_file" | head -n 1
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

ensure_checkout_clean() {
  checkout_status="$(git_status_without_generated_dist)" || return 1
  if [ -n "$checkout_status" ]; then
    echo "FAIL Tracked or untracked files have local changes; deployment will not overwrite them."
    printf '%s\n' "$checkout_status"
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
  expected_css="$(get_frontend_css "$expected_index")"
  if [ -z "$expected_bundle" ]; then
    echo "Cannot find built frontend JS bundle in $expected_index"
    return 1
  fi
  if [ -z "$expected_css" ]; then
    echo "Cannot find built frontend CSS bundle in $expected_index"
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
  served_css="$(get_frontend_css "$served_index")"
  echo "Built frontend bundle:  $expected_bundle"
  echo "Served frontend bundle: $served_bundle"
  echo "Built frontend CSS:  $expected_css"
  echo "Served frontend CSS: $served_css"

  if [ -n "$served_bundle" ] && [ "$expected_bundle" = "$served_bundle" ] &&
     [ -n "$served_css" ] && [ "$expected_css" = "$served_css" ]; then
    echo "OK  Frontend served bundle $expected_bundle"
    rm -f "$served_index"
    check_http_200 "Frontend JS bundle" "$served_url$expected_bundle" || return 1
    check_http_200 "Frontend CSS bundle" "$served_url$expected_css" || return 1
    return 0
  fi

  echo "FAIL Frontend served index does not reference built JS/CSS bundles."
  echo "Frontend pid: $(cat "$LOG_DIR/frontend.pid" 2>/dev/null || echo missing)"
  echo "Frontend dist: $ROOT_DIR/frontend/dist"
  echo "Current commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "Port ${FRONTEND_PORT:-3010} owner:"
  show_port_owner "${FRONTEND_PORT:-3010}"
  rm -f "$served_index"
  return 1
}

check_frontend_artifacts() {
  dist_dir="${1:-$ROOT_DIR/frontend/dist}"
  index_file="$dist_dir/index.html"
  if [ ! -s "$index_file" ]; then
    echo "FAIL Missing frontend build index: $index_file"
    return 1
  fi

  bundle="$(get_frontend_bundle "$index_file")"
  if [ -z "$bundle" ] || [ ! -s "$dist_dir/$bundle" ]; then
    echo "FAIL Missing frontend JS bundle referenced by $index_file: $bundle"
    return 1
  fi
  css_bundle="$(get_frontend_css "$index_file")"
  if [ -z "$css_bundle" ] || [ ! -s "$dist_dir/$css_bundle" ]; then
    echo "FAIL Missing frontend CSS bundle referenced by $index_file: $css_bundle"
    return 1
  fi

  # BALMUDA is also a current login product mark, so it cannot identify the removed intro.
  if grep -R -E "app-splash|너의 목소리" "$dist_dir" >/dev/null 2>&1; then
    echo "FAIL Removed intro content remains in frontend/dist."
    grep -R -l -E "app-splash|너의 목소리" "$dist_dir" || true
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
  echo "Built frontend CSS: $css_bundle"
}

restore_package_lock_if_only_dirty() {
  reason="$1"
  current_dir="$(pwd)"
  cd "$ROOT_DIR"

  status="$(git_status_without_generated_dist)" || return 1
  if [ -z "$status" ]; then
    cd "$current_dir"
    return 0
  fi

  other_changes="$(printf '%s\n' "$status" | grep -v '^.. frontend/package-lock\.json$' || true)"
  if [ -n "$other_changes" ]; then
    echo "Working tree is dirty. Commit, stash, or remove local changes before deploy."
    echo "Changed files:"
    git_status_without_generated_dist
    cd "$current_dir"
    return 1
  fi

  echo "$reason"
  echo "Only frontend/package-lock.json changed. Restoring it before continuing."
  git restore -- frontend/package-lock.json || {
    cd "$current_dir"
    return 1
  }

  status="$(git_status_without_generated_dist)" || return 1
  if [ -n "$status" ]; then
    echo "Working tree is still dirty after restoring frontend/package-lock.json."
    echo "Changed files:"
    printf '%s\n' "$status"
    cd "$current_dir"
    return 1
  fi

  cd "$current_dir"
  return 0
}

run_frontend_build() {
  candidate_dir="$1"
  echo "Running frontend build."
  if npm run build -- --outDir "$candidate_dir" > "$BUILD_LOG" 2>&1; then
    cat "$BUILD_LOG"
    echo "Frontend build completed."
    restore_package_lock_if_only_dirty "Checking for package-lock changes after frontend build." || return 1
    return 0
  fi

  echo "Frontend build failed."
  cat "$BUILD_LOG"

  if grep -E "@rollup/rollup-linux-x64-gnu|optional dependencies|removing both package-lock.json and node_modules" "$BUILD_LOG" >/dev/null 2>&1; then
    echo "Rollup optional dependency issue detected."
    echo "Recreating node_modules while preserving the tracked package-lock.json."
    rm -rf node_modules || return 1
    npm ci --include=optional --include=dev || return 1
    if [ ! -d "node_modules/@rollup/rollup-linux-x64-gnu" ]; then
      echo "Installing the Rollup Linux optional package without changing package-lock.json."
      npm install --no-save --package-lock=false @rollup/rollup-linux-x64-gnu || return 1
    fi

    echo "Retrying frontend build."
    if npm run build -- --outDir "$candidate_dir"; then
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
  ensure_checkout_clean || return 1
  if [ "$DEPLOY_MODE" = "pull" ]; then
    DEPLOY_STAGE="GIT_PULL"
    DEPLOY_REASON="Git pull failed; see the Git output above."
    pull_checkout || return 1
    DEPLOY_STAGE="GIT_CLEAN"
    DEPLOY_REASON="Working tree changed after Git pull."
    ensure_checkout_clean || return 1
    echo "Checkout after pull:"
    git log -1 --oneline || return 1
    git status --short || return 1
  else
    echo "Git pull skipped by --no-pull; deploying the current checkout."
  fi

  echo "== Backend dependency check =="
  DEPLOY_STAGE="BACKEND_PREPARE"
  DEPLOY_REASON="Backend dependency, import, or migration check failed."
  unset DATABASE_URL
  cd "$ROOT_DIR/backend"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv || return 1
  fi
  . .venv/bin/activate
  python -m pip install -r requirements.txt || return 1

  echo "== Backend compile and import check =="
  python -m compileall app || return 1
  python -c "from app.main import app; print('IMPORT_OK')" || return 1

  echo "== Alembic migration =="
  (
    set +x
    migration_env_file="${ASSET_MANAGER_MIGRATION_ENV:-$ROOT_DIR/deploy/.migration.env}"
    if [ ! -r "$migration_env_file" ]; then
      echo "MIGRATION_DATABASE_URL is required for database migrations." >&2
      exit 1
    fi
    set -a
    . "$migration_env_file"
    set +a
    if [ -z "${MIGRATION_DATABASE_URL:-}" ]; then
      echo "MIGRATION_DATABASE_URL is required for database migrations." >&2
      exit 1
    fi
    alembic current && alembic heads && alembic upgrade head
  ) || return 1

  echo "== Frontend build =="
  DEPLOY_STAGE="FRONTEND_BUILD"
  DEPLOY_REASON="Frontend candidate build or artifact validation failed."
  cd "$ROOT_DIR/frontend"
  if [ -f "package-lock.json" ]; then
    npm ci --include=optional --include=dev || return 1

    restore_package_lock_if_only_dirty \
      "Checking for package-lock changes after npm ci." || return 1
  else
    npm install || return 1

    restore_package_lock_if_only_dirty \
      "Checking for package-lock changes after npm install." || return 1
  fi
  CANDIDATE_DIST="$ROOT_DIR/frontend/dist.next.$$"
  if [ -e "$CANDIDATE_DIST" ]; then
    echo "FAIL Frontend candidate directory already exists: $CANDIDATE_DIST"
    return 1
  fi
  CANDIDATE_CREATED=true
  run_frontend_build "$CANDIDATE_DIST" || return 1
  check_frontend_artifacts "$CANDIDATE_DIST" || return 1

  echo "== Frontend browser prerequisite =="
  DEPLOY_STAGE="FRONTEND_BROWSER_PRECHECK"
  DEPLOY_REASON="Headless Chromium precheck failed; frontend and backend were not restarted."
  check_frontend_browser_availability || return 1

  echo "== Stop backend (frontend remains online) =="
  DEPLOY_STAGE="STOP_BACKEND"
  DEPLOY_REASON="Could not identify or stop the existing backend on port ${BACKEND_PORT:-8010}; frontend was not stopped."
  "$ROOT_DIR/deploy/stop_backend.sh" || return 1

  echo "== Start and verify backend =="
  DEPLOY_STAGE="START_BACKEND"
  DEPLOY_REASON="New backend did not start or remain healthy; frontend was not stopped."
  start_backend_once || return 1
  check_current_backend || return 1

  echo "== Stop frontend =="
  DEPLOY_STAGE="STOP_FRONTEND"
  DEPLOY_REASON="Could not stop the existing frontend; dist was not changed."
  if ! "$ROOT_DIR/deploy/stop_frontend.sh"; then
    "$ROOT_DIR/deploy/start_frontend.sh" || true
    return 1
  fi

  echo "== Replace frontend dist =="
  DEPLOY_STAGE="FRONTEND_CUTOVER"
  DEPLOY_REASON="Frontend dist replacement or startup failed."
  PREVIOUS_DIST="$ROOT_DIR/frontend/dist.previous.$$"
  if [ -e "$PREVIOUS_DIST" ]; then
    echo "FAIL Frontend previous directory already exists: $PREVIOUS_DIST"
    "$ROOT_DIR/deploy/start_frontend.sh" || true
    return 1
  fi
  if [ -d "$ROOT_DIR/frontend/dist" ]; then
    if ! mv -- "$ROOT_DIR/frontend/dist" "$PREVIOUS_DIST"; then
      "$ROOT_DIR/deploy/start_frontend.sh" || true
      return 1
    fi
  fi
  if ! mv -- "$CANDIDATE_DIST" "$ROOT_DIR/frontend/dist"; then
    rollback_frontend_or_report
    return 1
  fi
  CANDIDATE_DIST=""
  CANDIDATE_CREATED=false
  if ! "$ROOT_DIR/deploy/start_frontend.sh"; then
    rollback_frontend_or_report
    return 1
  fi
  if ! check_http_200 "Frontend after start" "http://127.0.0.1:${FRONTEND_PORT:-3010}/"; then
    rollback_frontend_or_report
    return 1
  fi

  echo "== Health check =="
  DEPLOY_STAGE="HEALTH_CHECK"
  DEPLOY_REASON="Final health, CORS, or frontend bundle verification failed."
  if ! "$ROOT_DIR/deploy/health_check.sh" ||
     ! check_cors_origin "http://192.168.222.210:3010" ||
     ! check_cors_origin "http://112.216.230.162:3010" ||
     ! verify_frontend_bundle; then
    rollback_frontend_or_report
    return 1
  fi

  echo "== Frontend browser smoke test =="
  DEPLOY_STAGE="FRONTEND_BROWSER_SMOKE"
  DEPLOY_REASON="Frontend did not render correctly in headless Chromium."
  if [ "$BROWSER_SMOKE_AVAILABLE" = true ]; then
    if ! run_frontend_browser_smoke; then
      BROWSER_SMOKE_STATUS="FAIL"
      rollback_frontend_or_report
      return 1
    fi
    BROWSER_SMOKE_STATUS="PASS"
  else
    echo "Browser Smoke Test: SKIPPED (browser unavailable)"
  fi

  echo "== Direct endpoint check =="
  if ! check_current_backend ||
     ! check_http_200 "Frontend" "http://127.0.0.1:${FRONTEND_PORT:-3010}/"; then
    rollback_frontend_or_report
    return 1
  fi
  if [ -d "$PREVIOUS_DIST" ]; then
    rm -rf -- "$PREVIOUS_DIST" || return 1
  fi
  echo "== Deployment complete =="
  echo "Frontend: http://127.0.0.1:${FRONTEND_PORT:-3010}"
  echo "Backend:  http://127.0.0.1:${BACKEND_PORT:-8010}"
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

if [ "$DEPLOY_MODE" != "check" ]; then
  report_deploy_result >> "$TMP_LOG"
fi
tee -a "$LOG_FILE" < "$TMP_LOG"
exit "$DEPLOY_STATUS"
