#!/usr/bin/env bash
set -euo pipefail

# 배포 초안:
# 1. NAS 운영 경로로 이동
# 2. git pull로 최신 코드 반영
# 3. 필요한 환경변수 또는 deploy/.env 확인
# 4. docker compose config로 설정 검증
# 5. docker compose up -d로 서비스 재기동

git pull
docker compose config
docker compose up -d
