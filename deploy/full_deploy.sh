#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_DIR="/volume6/총무/서버/자산관리 프로젝트/asset-manager-web"

cd -- "$PROJECT_DIR"

if [[ ! -d .git ]]; then
  echo "ERROR: Git repository not found: $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -x deploy/deploy.sh ]]; then
  echo "ERROR: Deployment script is missing or not executable." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
current_commit="$(git rev-parse --short HEAD)"
echo "Project: $PROJECT_DIR"
echo "Current branch: ${current_branch:-DETACHED_HEAD}"
echo "Current commit: $current_commit"

echo "[1/2] Pulling the latest Git changes..."
if ! git pull --ff-only; then
  echo "========================================"
  echo "DEPLOY FAILED"
  echo "Stage: GIT_PULL"
  echo "Reason: Git pull --ff-only failed."
  echo "Current frontend: UNCHANGED"
  echo "Current backend: UNCHANGED"
  echo "========================================"
  exit 1
fi
echo "Updated commit: $(git rev-parse --short HEAD)"

echo "[2/2] Running deployment, migration, and final health checks..."
"$PROJECT_DIR/deploy/deploy.sh" --no-pull

echo "Asset Manager 운영 배포가 완료되었습니다."
