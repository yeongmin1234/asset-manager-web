# Deployment Readiness

이 문서는 NAS 직접 실행 배포 전 체크리스트입니다. 실제 NAS 접속, 서비스 중지, DB 접속은 이 단계에서 수행하지 않습니다.

## 배포 기준

- 배포 방식: Docker 미사용 NAS 직접 실행
- 운영 대상: 내부용 자산관리 시스템
- 실행 경로: `/volume6/총무/서버/자산관리 프로젝트/asset-manager-web`
- Frontend: `frontend/dist` 정적 파일 제공
- Backend: Python venv + uvicorn
- DB: 신규 자산관리 전용 PostgreSQL 또는 전용 DB

## 포함 대상

- `backend/`
- `frontend/`
- `deploy/`
- `docs/`
- `README.md`
- `.gitignore`

## 제외 대상

- `backend/.env`, `frontend/.env`, `deploy/.env`
- `backend/.venv/`, `venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`, `*.pyc`
- `logs/`, `*.log`
- `backups/`, `*.sql`, `*.dump`

## 포트 체크

사용 예정:

- Frontend: `3010`
- Backend: `8001`
- PostgreSQL: `5432`

사용 금지:

- `80`
- `8080`

실제 NAS 포트 충돌 여부는 배포 단계에서 사용자가 직접 확인합니다.

## 배포 전 준비

1. NAS 전용 경로에 프로젝트 파일을 배치합니다.
2. `backend/.env` 또는 `deploy/.env`를 예시 파일 기준으로 작성합니다.
3. Backend venv를 생성하고 의존성을 설치합니다.
4. Frontend build를 실행합니다.
5. `chmod +x deploy/*.sh`로 스크립트 실행 권한을 부여합니다.
6. `deploy/start_all.sh`로 신규 자산관리 프로세스만 시작합니다.
7. `deploy/health_check.sh`로 상태를 확인합니다.

## 보안 원칙

- 실제 `.env`와 DB 백업 파일은 Git에 올리지 않습니다.
- 기존 SCM MySQL 접속 정보는 사용하지 않습니다.
- 외부 공개 전에는 인증 또는 접근 제한을 별도 검토합니다.
