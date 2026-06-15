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
BACKUP_DIR="$ROOT_DIR/backups/db"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

DATABASE_URL="${DATABASE_URL:-}"
POSTGRES_DB="${POSTGRES_DB:-asset_manager_prod}"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is not set. Create deploy/.env or set ASSET_MANAGER_ENV."
  exit 1
fi

echo "Backing up asset manager PostgreSQL database only."
echo "Output: $BACKUP_FILE"
pg_dump "$DATABASE_URL" -Fc -f "$BACKUP_FILE"
echo "Backup complete."
