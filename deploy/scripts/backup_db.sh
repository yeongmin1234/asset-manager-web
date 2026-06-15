#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/volume6/총무/서버/자산관리 프로젝트/backups/db"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/asset_manager_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

: "${POSTGRES_DB:=asset_manager}"
: "${POSTGRES_USER:=asset_user}"
: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"

pg_dump \
  --host "${POSTGRES_HOST}" \
  --port "${POSTGRES_PORT}" \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --file "${BACKUP_FILE}"

echo "Database backup created: ${BACKUP_FILE}"
