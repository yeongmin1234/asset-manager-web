# Deploy Scripts

이 폴더는 Docker를 사용하지 않는 NAS 직접 실행 운영 스크립트를 둡니다.

## 운영 기준

- Backend: Python venv + uvicorn, 포트 `8010`
- Frontend: `frontend/dist` 정적 파일 제공, 포트 `3010`
- DB: 신규 자산관리 전용 PostgreSQL 또는 전용 DB
- 금지 포트: `80`, `8080`
- 기존 SCM 서버, SCM MySQL, NAS 서비스는 변경하지 않습니다.
- `full_deploy.sh`와 `deploy.sh`의 자동 실행 경로는 Docker 컨테이너를 중지하거나 재시작하지 않습니다.

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

Alembic은 `MIGRATION_DATABASE_URL`이 있어야 실행됩니다. `deploy/migration.env.example`을 참고하여
`deploy/.migration.env`를 만들고 NAS에서 읽을 수 있는 계정을 제한합니다(`chmod 600`).
파일을 공유 프로젝트 밖에 두려면 `ASSET_MANAGER_MIGRATION_ENV`에 그 경로를 지정할 수 있습니다.
`MIGRATION_DATABASE_URL`을 `backend/.env` 또는 `deploy/.env`에 넣지 마세요. 배포 스크립트는
migration 명령을 실행하는 서브셸에서만 전용 파일을 읽으며, 파일이 없으면 Backend 중지 전
`BACKEND_PREPARE` 단계에서 실패합니다. 전용 DB Role이 준비되기 전까지 운영 배포도 이 단계에서
중단되므로, Role 생성 단계에서 파일을 설정하고 접속을 검증한 뒤 배포해야 합니다.

## 프론트엔드 브라우저 검증

`full_deploy.sh`는 기존 HTTP·bundle·backend 검사 후 브라우저가 있으면 `frontend_smoke_test.mjs`를 실행합니다. 로그인 폼 또는 앱 화면이 렌더링되고 JavaScript 오류와 핵심 JS/CSS 로딩 실패가 없는 경우 `PASS`입니다. 브라우저 검사 실패 시 이전 `dist`를 복원하고 재검사합니다.

NAS에 Chromium/Chrome 실행 파일이 없다면 `SKIPPED (browser unavailable)` 경고 후 배포를 계속합니다. 이 경우에도 build 파일의 JS·CSS 존재 및 크기, 운영 HTTP 200, 운영 index의 JS·CSS 참조 일치, 각 JS·CSS URL의 HTTP 200이 필수입니다. 브라우저 실행 파일은 있지만 실행에 실패하면 배포를 중단합니다.

브라우저 검사를 사용하려면 `FRONTEND_SMOKE_BROWSER_PATH`에 실행 파일을 지정할 수 있습니다. NAS에서 브라우저를 실행할 수 없다면 내부 테스트 PC의 Chrome CDP 주소를 `FRONTEND_SMOKE_CDP_URL`로, 그 PC에서 접근 가능한 프론트엔드 주소를 `FRONTEND_SMOKE_URL`로 설정합니다.

개발 PC에서는 production build를 만든 뒤 별도 포트로 정적 파일을 제공하여 검사할 수 있습니다.

```sh
cd frontend
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
# 다른 터미널에서
npm run smoke:test -- http://127.0.0.1:4173/
```

## Docker 보류

기존 검토용 Docker/Compose 방식은 운영 기준에서 제외합니다. 실제 운영 절차에는 Docker 명령을 사용하지 않습니다.
