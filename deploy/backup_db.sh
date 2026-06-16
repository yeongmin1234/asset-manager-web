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

is_placeholder_database_url() {
  case "${1:-}" in
    *CHANGE_ME*|*change_me*)
      return 0
      ;;
  esac
  return 1
}

DATABASE_URL="${DATABASE_URL:-}"
if [ -z "$DATABASE_URL" ] || is_placeholder_database_url "$DATABASE_URL"; then
  unset DATABASE_URL
  BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"
  if [ -f "$BACKEND_ENV_FILE" ]; then
    set -a
    . "$BACKEND_ENV_FILE"
    set +a
  fi
  DATABASE_URL="${DATABASE_URL:-}"
fi

POSTGRES_DB="${POSTGRES_DB:-asset_manager_prod}"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"

if [ -z "$DATABASE_URL" ]; then
  echo "Database backup failed: DATABASE_URL is not configured."
  exit 1
fi

if is_placeholder_database_url "$DATABASE_URL"; then
  echo "Database backup failed: placeholder database credentials detected."
  exit 1
fi

PG_DUMP_URL="$(printf '%s' "$DATABASE_URL" | sed 's#^postgresql+psycopg://#postgresql://#')"

echo "Backing up asset manager PostgreSQL database only."
echo "Output: $BACKUP_FILE"
if pg_dump "$PG_DUMP_URL" -Fc -f "$BACKUP_FILE"; then
  echo "Backup complete."
else
  echo "Database backup failed: pg_dump did not complete."
  exit 1
fi
