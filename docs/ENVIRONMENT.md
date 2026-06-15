# Environment

자산관리 시스템의 환경변수와 비밀값 관리 기준입니다.

## 원칙

- 실제 `.env` 파일은 Git에 포함하지 않습니다.
- `.env.example`에는 예시값과 `CHANGE_ME`만 둡니다.
- 기존 SCM MySQL, 기존 NAS 서비스, 기존 서버 환경변수는 사용하지 않습니다.
- Docker/Compose 운영 기준은 보류하며, NAS 직접 실행 기준으로 작성합니다.

## Backend 예시

`backend/.env.example` 또는 NAS의 실제 `backend/.env` 작성 기준:

```env
APP_NAME=Asset Manager
APP_ENV=production
DATABASE_URL=postgresql+psycopg://asset_user:CHANGE_ME@127.0.0.1:5432/asset_manager_prod
CORS_ORIGINS=http://192.168.222.210:3010
UPLOAD_DIR=../uploads
EXPORT_DIR=../exports
SECRET_KEY=CHANGE_ME
```

`DATABASE_URL`은 신규 자산관리 전용 PostgreSQL만 가리켜야 합니다.

## Frontend 예시

정적 빌드 전에 API 주소를 지정합니다.

```env
VITE_API_BASE_URL=http://192.168.222.210:8001
```

Frontend 접속 포트는 `3010`, Backend 포트는 `8001`을 사용합니다. 포트 `80`, `8080`은 사용하지 않습니다.

## deploy/.env 예시

`deploy/env.example`을 복사해 NAS에서 `deploy/.env`로 사용할 수 있습니다.

```sh
cp deploy/env.example deploy/.env
```

실제 비밀번호는 `CHANGE_ME`를 변경해 사용하되 Git에 포함하지 않습니다.
