#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

mkdir -p "$ROOT_DIR/logs"

"$ROOT_DIR/deploy/start_backend.sh"
"$ROOT_DIR/deploy/start_frontend.sh"

echo "Asset Manager services started."
