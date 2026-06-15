# NAS Direct Deployment

이 문서는 9-2 단계의 NAS 직접 실행 배포 준비 문서입니다. 실제 NAS 접속과 배포 실행은 다음 단계에서 사용자 확인 후 진행합니다.

## 운영 방향

- Docker와 Docker Compose는 사용하지 않습니다.
- 혼자 사용하는 내부용 자산관리 시스템 기준으로 운영합니다.
- 기존 서버, 기존 SCM, 기존 SCM MySQL, 기존 NAS 서비스와 분리합니다.
- 신규 자산관리 전용 경로, 프로세스, 로그, DB만 사용합니다.
- 호스트 포트 `80`, `8080`은 사용하지 않습니다.

## 배포 예정 경로

Windows 공유 경로:

```text
\\192.168.222.210\총무\서버\자산관리 프로젝트\asset-manager-web
```

NAS 내부 경로:

```text
/volume6/총무/서버/자산관리 프로젝트/asset-manager-web
```

## 포트 정책

- Frontend 정적 서버: `3010`
- Backend FastAPI: `8001`
- PostgreSQL: `5432` 또는 NAS 내부 전용 포트
- 금지 포트: `80`, `8080`

예상 접속 주소:

```text
http://192.168.222.210:3010
```

## Backend 운영 구조

Backend는 Python venv와 uvicorn으로 직접 실행합니다.

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

운영 환경변수는 `backend/.env` 또는 `deploy/.env`에 둡니다. 실제 `.env`는 Git에 포함하지 않습니다.

## Frontend 운영 구조

Frontend는 NAS에서 개발 서버로 실행하지 않습니다. `npm run build`로 만든 정적 파일을 제공합니다.

```sh
cd frontend
npm install
npm run build
```

이번 단계의 기본 스크립트는 Python 정적 서버로 `frontend/dist`를 제공합니다.

```sh
python3 -m http.server 3010 --bind 0.0.0.0 --directory frontend/dist
```

NAS Web Station 또는 별도 정적 서버 방식은 실제 배포 단계에서 검토합니다.

## 실행 스크립트

실행 권한은 NAS에서 1회 부여합니다.

```sh
chmod +x deploy/*.sh
```

주요 스크립트:

- `deploy/start_backend.sh`: Backend 시작
- `deploy/stop_backend.sh`: Backend 중지
- `deploy/start_frontend.sh`: Frontend 정적 서버 시작
- `deploy/stop_frontend.sh`: Frontend 정적 서버 중지
- `deploy/start_all.sh`: Backend와 Frontend 시작
- `deploy/stop_all.sh`: Backend와 Frontend 중지
- `deploy/deploy.sh`: 의존성 확인, Frontend build, 재시작, health check
- `deploy/health_check.sh`: Frontend, Backend, DB health 확인
- `deploy/rotate_logs.sh`: 오래된 로그 정리 대상 확인
- `deploy/backup_db.sh`: 자산관리 전용 PostgreSQL 백업

`deploy/deploy.sh`는 Git 업데이트를 자동 실행하지 않습니다. 배포 파일 반영 후 사용자가 직접 실행하는 구조입니다.

## 로그 구조

신규 자산관리 전용 로그만 사용합니다.

```text
logs/backend.log
logs/frontend.log
logs/deploy.log
logs/health_check.log
```

`logs/`는 Git에 포함하지 않습니다.

## DB 운영 구조

- 기존 SCM MySQL은 사용하지 않습니다.
- 신규 자산관리 전용 PostgreSQL 또는 전용 운영 DB만 사용합니다.
- 이번 단계에서는 실제 DB 생성, 접속, migration 실행을 하지 않습니다.
- 운영 DB 연결 정보는 `.env.example`에 예시로만 둡니다.
- migration은 운영 DB 백업 후 별도 승인 단계에서만 실행합니다.

운영 예시:

```env
DATABASE_URL=postgresql+psycopg://asset_user:CHANGE_ME@127.0.0.1:5432/asset_manager_prod
```

## 백업 방향

`deploy/backup_db.sh`는 자산관리 전용 PostgreSQL만 대상으로 합니다.

- 백업 폴더: `backups/db`
- 백업 파일명: DB명 + 날짜/시간
- 실제 비밀번호는 스크립트에 쓰지 않고 env에서 읽습니다.
- 기존 SCM/MySQL 백업은 수행하지 않습니다.

## Docker 방식 보류

이전 검토 중 작성된 Docker/Compose 방식은 이번 운영 기준에서 제외합니다. 실제 운영 절차에는 Docker 명령을 사용하지 않습니다.
