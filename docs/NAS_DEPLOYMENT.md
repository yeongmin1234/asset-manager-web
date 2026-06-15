# NAS Deployment

운영 기준 경로:

```text
/volume6/총무/서버/자산관리 프로젝트/
├─ app/
│  ├─ backend/
│  └─ frontend/
├─ deploy/
├─ postgres/
│  └─ data/
├─ uploads/
│  └─ asset-images/
├─ exports/
├─ backups/
│  ├─ db/
│  └─ files/
├─ logs/
│  ├─ backend/
│  ├─ frontend/
│  └─ postgres/
└─ docs/
```

## 폴더 역할

- `app/backend`: FastAPI 백엔드 애플리케이션 코드
- `app/frontend`: React + Vite 프론트엔드 애플리케이션 코드
- `deploy`: Docker Compose 및 운영 스크립트
- `postgres/data`: PostgreSQL 운영 데이터
- `uploads/asset-images`: 자산 이미지 업로드 파일
- `exports`: 엑셀 등 내보내기 결과 파일
- `backups/db`: PostgreSQL 백업 파일
- `backups/files`: 업로드 파일 등 파일 백업
- `logs/backend`: 백엔드 로그
- `logs/frontend`: 프론트엔드 로그
- `logs/postgres`: PostgreSQL 로그
- `docs`: 운영 및 요구사항 문서

## 운영 주의사항

- `postgres/data` 폴더는 운영 DB 데이터이므로 삭제 금지
- `backups` 폴더는 운영 백업 데이터이므로 삭제 금지
- `.env` 파일은 Git에 업로드 금지
- `uploads`, `exports`, `backups`, `logs`는 Git에 업로드 금지
- SCM MySQL DB와 연결하지 않음
- 자산관리 전용 PostgreSQL을 별도 운영
- 포트 `80`, `8080`은 기존 SCM 또는 NAS 내부 서비스와 충돌할 수 있으므로 사용하지 않음
- Frontend 배포 외부 포트는 `3010`, Backend 배포 외부 포트는 `8010` 사용
- PostgreSQL은 내부 `5432`를 사용하되 외부 `ports` 매핑 없이 backend 컨테이너에서만 접근하는 구성을 우선 적용

## 운영 DB 마이그레이션 원칙

- NAS에서 바로 `alembic upgrade head`를 실행하지 않습니다.
- 운영 반영 전 자산관리 전용 PostgreSQL 백업을 먼저 수행합니다.
- 기존 서버, 기존 서비스, 기존 Docker 컨테이너, 기존 NAS 서비스 설정은 변경하지 않습니다.
- 기존 SCM MySQL DB에는 접속하지 않습니다.
- migration은 신규 자산관리 PostgreSQL에만 적용합니다.
- 포트 `80`, `8080`은 사용하지 않습니다.
- `postgres/data` 삭제 금지
- `backups` 삭제 금지
- 이번 단계에서는 `deploy.sh` 등 배포 스크립트에 자동 migration 실행을 넣지 않습니다.
