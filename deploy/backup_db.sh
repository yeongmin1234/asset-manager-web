#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups/db"
ENV_FILE="${ASSET_MANAGER_ENV:-$ROOT_DIR/deploy/.env}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-asset_manager_prod}"
POSTGRES_USER="${POSTGRES_USER:-asset_user}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"

echo "Backing up asset manager PostgreSQL database only."
echo "Output: $BACKUP_FILE"
pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" -f "$BACKUP_FILE"
echo "Backup complete."
