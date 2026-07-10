#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/volume6/총무/서버/자산관리 프로젝트/asset-manager-web"

cd -- "$PROJECT_DIR"

if [[ ! -d .git ]]; then
  echo "ERROR: Git repository not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -x backend/.venv/bin/alembic ]]; then
  echo "ERROR: Alembic executable not found: $PROJECT_DIR/backend/.venv/bin/alembic" >&2
  exit 1
fi

if [[ ! -x deploy/deploy.sh || ! -x deploy/health_check.sh ]]; then
  echo "ERROR: Existing deployment scripts are missing or not executable." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
current_commit="$(git rev-parse --short HEAD)"
echo "Project: $PROJECT_DIR"
echo "Current branch: ${current_branch:-DETACHED_HEAD}"
echo "Current commit: $current_commit"

echo "[1/4] Pulling the latest Git changes..."
git pull --ff-only
echo "Updated commit: $(git rev-parse --short HEAD)"

echo "[2/4] Applying backend Alembic migrations..."
(
  cd -- "$PROJECT_DIR/backend"
  ./.venv/bin/alembic upgrade head
)

echo "[3/4] Running the existing deployment script..."
"$PROJECT_DIR/deploy/deploy.sh" --no-pull

echo "[4/4] Running deployment health checks..."
"$PROJECT_DIR/deploy/health_check.sh"

echo "Asset Manager 운영 배포가 완료되었습니다."
