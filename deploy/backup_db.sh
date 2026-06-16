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

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-asset-postgres}"
POSTGRES_DB="${POSTGRES_DB:-asset_manager_prod}"
POSTGRES_USER="${POSTGRES_USER:-asset_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"
TMP_BACKUP_FILE="$BACKUP_FILE.tmp"

if [ -n "${DATABASE_URL:-}" ] && is_placeholder_database_url "$DATABASE_URL"; then
  echo "Database backup failed: placeholder database credentials detected."
  exit 1
fi

if is_placeholder_database_url "$POSTGRES_PASSWORD"; then
  echo "Database backup failed: placeholder database credentials detected."
  exit 1
fi

DOCKER_CMD=""
if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
  DOCKER_CMD="docker"
elif command -v sudo >/dev/null 2>&1 && sudo docker ps >/dev/null 2>&1; then
  DOCKER_CMD="sudo docker"
else
  echo "Database backup failed: docker is not available or permission is denied."
  echo "Check Docker permission or sudo docker access for the current user."
  exit 1
fi

echo "Backing up asset manager PostgreSQL database only."
echo "Output: $BACKUP_FILE"
rm -f "$TMP_BACKUP_FILE"
if [ -n "$POSTGRES_PASSWORD" ]; then
  if ! $DOCKER_CMD exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$POSTGRES_CONTAINER" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c > "$TMP_BACKUP_FILE"; then
    rm -f "$TMP_BACKUP_FILE"
    echo "Database backup failed: container pg_dump did not complete."
    exit 1
  fi
else
  if ! $DOCKER_CMD exec "$POSTGRES_CONTAINER" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c > "$TMP_BACKUP_FILE"; then
    rm -f "$TMP_BACKUP_FILE"
    echo "Database backup failed: container pg_dump did not complete."
    exit 1
  fi
fi

if [ -s "$TMP_BACKUP_FILE" ]; then
  mv "$TMP_BACKUP_FILE" "$BACKUP_FILE"
  BACKUP_SIZE="$(wc -c < "$BACKUP_FILE" | tr -d ' ')"
  echo "Database backup completed."
  echo "Backup size: ${BACKUP_SIZE} bytes"
else
  rm -f "$TMP_BACKUP_FILE"
  echo "Database backup failed: dump file was not created."
  exit 1
fi
