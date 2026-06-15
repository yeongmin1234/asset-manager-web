#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

"$ROOT_DIR/deploy/stop_frontend.sh"
"$ROOT_DIR/deploy/stop_backend.sh"

echo "Asset Manager services stopped."
