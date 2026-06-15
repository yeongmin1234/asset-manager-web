# Asset Manager Web

React + FastAPI + PostgreSQL 기반의 사내 자산관리 시스템 기본 구조입니다.

이번 단계에서는 로컬 PostgreSQL 개발 DB, Alembic migration, seed 데이터, 자산 CRUD API, 변경 이력, 자산 빠른 등록, 자산 현황/분류별/부서별/월별 통계(최근 3개월), 엑셀 내보내기/가져오기 보조 기능, 포털형 프론트엔드 화면, NAS 직접 실행 운영 문서를 포함합니다.
프론트엔드는 업무용 SaaS 대시보드 톤으로 정리되어 PC/노트북에서는 빠른 등록, 넓은 목록과 통계 카드 중심으로, 모바일에서는 1열 반응형으로 표시됩니다.

## 기술 스택

- Frontend: React + Vite
- Backend: FastAPI
- Database: PostgreSQL
- DB Driver: psycopg, SQLAlchemy
- Deploy: NAS direct run scripts
- Server: Synology NAS

## 개발용 Backend 실행

로컬 PostgreSQL 17의 개발 DB `asset_manager_dev` 설정, migration, seed, API 검증 절차는 `docs/LOCAL_DB_SETUP.md`를 먼저 확인하세요. 실제 DB 비밀번호는 `backend/.env`에만 두고 GitHub에 올리지 않습니다.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

확인:

- http://localhost:8001/health
- http://localhost:8001/health/db
- http://localhost:8001/docs

## 개발용 Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

확인:

- http://localhost:5173

## Windows 로컬 개발 BAT 실행

프로젝트 루트의 BAT 파일은 배포용이 아니라 로컬 PC 개발용입니다. 운영 NAS 배포, 운영 DB, 기존 서버/SCM/MySQL에는 연결하거나 변경하지 않습니다.

Backend만 실행:

```bat
dev_backend.bat
```

Frontend만 실행:

```bat
dev_frontend.bat
```

Backend와 Frontend를 각각 새 cmd 창으로 실행:

```bat
dev_start_all.bat
```

접속 주소:

- Backend: http://127.0.0.1:8001
- Frontend: http://127.0.0.1:5173/

## 포트 기준

- Frontend 개발 서버: `5173`
- Backend 개발 서버: `8001`
- Frontend 운영 포트: `3010`
- Backend 운영 포트: `8001`
- PostgreSQL: 신규 자산관리 전용 DB `5432` 또는 NAS 내부 전용 포트
- 포트 `80`, `8080`은 기존 SCM 또는 NAS 내부 서비스와 충돌할 수 있으므로 절대 사용하지 않습니다.

## 검증 명령

Backend:

```bash
cd backend
python -m compileall app
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run build
```

## NAS 운영 경로

Synology NAS 운영 경로는 다음을 기준으로 합니다.

```text
/volume6/총무/서버/자산관리 프로젝트
```

자세한 폴더 구조와 운영 주의사항은 `docs/NAS_DEPLOYMENT.md`에 정리했습니다.

NAS 배포 전 구조 점검은 다음 문서를 함께 확인하세요.

- `docs/DEPLOYMENT.md`
- `docs/ENVIRONMENT.md`
- `docs/NAS_DIRECT_DEPLOYMENT.md`
- `docs/NAS_DEPLOYMENT.md`

NAS 운영은 Docker/Compose를 사용하지 않는 직접 실행 방식으로 정리합니다. `deploy/*.sh` 스크립트는 다음 단계에서 NAS 배포 전 사용자 확인 후 실행합니다.

## 제외된 기능

- 로그인 및 권한관리
- QR/바코드 기능
- 실제 NAS 배포
- 실제 운영 DB 접속
