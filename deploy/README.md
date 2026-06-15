# Deploy Scripts

이 폴더는 Docker를 사용하지 않는 NAS 직접 실행 운영 스크립트를 둡니다.

## 운영 기준

- Backend: Python venv + uvicorn, 포트 `8001`
- Frontend: `frontend/dist` 정적 파일 제공, 포트 `3010`
- DB: 신규 자산관리 전용 PostgreSQL 또는 전용 DB
- 금지 포트: `80`, `8080`
- 기존 SCM 서버, SCM MySQL, NAS 서비스는 변경하지 않습니다.

## 스크립트

- `start_backend.sh`
- `stop_backend.sh`
- `start_frontend.sh`
- `stop_frontend.sh`
- `start_all.sh`
- `stop_all.sh`
- `deploy.sh`
- `health_check.sh`
- `rotate_logs.sh`
- `backup_db.sh`
- `check_ports.sh`

NAS에서 실행 전 권한을 부여합니다.

```sh
chmod +x deploy/*.sh
```

## 환경변수

`deploy/env.example`을 참고해 `deploy/.env`를 작성할 수 있습니다. 실제 `.env`는 Git에 포함하지 않습니다.

## Docker 보류

기존 검토용 Docker/Compose 방식은 운영 기준에서 제외합니다. 실제 운영 절차에는 Docker 명령을 사용하지 않습니다.
