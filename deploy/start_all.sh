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

mkdir -p "$ROOT_DIR/logs"

"$ROOT_DIR/deploy/start_backend.sh"
"$ROOT_DIR/deploy/start_frontend.sh"

echo "Asset Manager services started."
"$ROOT_DIR/deploy/health_check.sh"
