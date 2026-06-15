# Backend

FastAPI 기반 자산관리 백엔드 기본 구조입니다. 현재 상태 확인 API, PostgreSQL 연결 확인 구조, SQLAlchemy 모델, Alembic 마이그레이션 준비 구조를 포함합니다.

## DB 모델

SQLAlchemy 모델과 Pydantic 스키마 기본 구조가 준비되어 있습니다.

- `assets`
- `asset_history`
- `categories`
- `departments`

이번 단계에서는 실제 운영 DB 테이블 생성 없이 로컬 개발 DB 기준 API 구조만 준비합니다. DB 설계 상세는 `../docs/DB_SCHEMA.md`를 참고하세요.

## 마이그레이션

Alembic은 `backend` 폴더 기준으로 실행합니다. DB URL은 환경변수 또는 `.env`의 `DATABASE_URL`을 `app.core.config.settings`가 읽는 구조입니다. 실제 비밀번호는 코드와 `alembic.ini`에 넣지 않습니다.

FastAPI 앱 시작 시 `Base.metadata.create_all()` 또는 `alembic upgrade head`를 자동 실행하지 않습니다. 마이그레이션은 개발자가 명령어로 수동 실행합니다.

로컬 개발 DB 예시:

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev"
```

Linux/macOS:

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev"
```

Windows 로컬 PostgreSQL 17 기준 전체 설정 절차는 `../docs/LOCAL_DB_SETUP.md`를 참고하세요.

Backend 문법 검증:

```powershell
cd backend
python -m compileall app
```

Alembic 도움말 확인:

```powershell
cd backend
alembic --help
```

Alembic 현재 상태 확인:

```powershell
cd backend
alembic current
```

마이그레이션 생성 예시:

```powershell
cd backend
alembic revision --autogenerate -m "create asset tables"
```

마이그레이션 적용 예시:

```powershell
cd backend
alembic upgrade head
```

로컬 개발 DB에 테이블이 생성되었는지 확인하는 예시:

```powershell
cd backend
alembic current
```

`psql`을 사용할 수 있다면 다음 테이블을 확인합니다.

```sql
\dt
SELECT id, name, sort_order, is_active FROM categories ORDER BY sort_order, id;
SELECT id, name, sort_order, is_active FROM departments ORDER BY sort_order, id;
```

수동 seed 실행 예시:

```powershell
cd backend
python -m app.db.seed
```

`python -m app.db.seed`는 개발자가 직접 실행할 때만 동작합니다. 앱 시작, migration 실행, health check 중 자동으로 실행되지 않습니다. 현재 seed 명령은 기본 categories/departments 후보를 추가하며, 같은 이름이 이미 있으면 중복 insert하지 않습니다.

주의:

- `alembic upgrade head`는 로컬 개발 DB에서만 실행하세요.
- 실제 NAS 운영 DB에는 아직 실행하지 마세요.
- 운영 DB 반영은 별도 배포 단계에서 백업 후 진행해야 합니다.
- 기존 SCM MySQL에는 접속하지 않습니다.
- seed 데이터는 앱 시작, migration 실행 중 자동 insert하지 않습니다.
- `APP_ENV=production` 상태에서는 수동 seed 명령도 실행을 거부합니다.

## 개발 실행

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

## NAS 직접 실행 기준

운영 NAS에서는 Docker를 사용하지 않고 Python venv와 uvicorn으로 직접 실행합니다.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

운영 환경변수는 `backend/.env` 또는 `deploy/.env`에 작성하되 Git에는 포함하지 않습니다. 운영 DB는 기존 SCM MySQL이 아닌 신규 자산관리 전용 PostgreSQL 또는 전용 DB만 사용합니다.

## 로컬 개발 CORS

FastAPI는 로컬 frontend 개발 서버에서 API를 호출할 수 있도록 제한된 origin만 허용합니다.

허용 origin:

- `http://127.0.0.1:5173`
- `http://localhost:5173`

`allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`를 사용합니다. 운영 환경에서 무분별한 전체 origin `"*"` 허용으로 고정하지 않습니다. CORS 설정 변경 후에는 backend 개발 서버를 재시작하거나 `--reload`가 반영되었는지 확인하세요.

## 확인 URL

- http://localhost:8001/health
- http://localhost:8001/health/db
- http://localhost:8001/assets
- http://localhost:8001/assets/1
- http://localhost:8001/categories
- http://localhost:8001/departments
- http://localhost:8001/stats/summary
- http://localhost:8001/docs

`/health/db`는 PostgreSQL 연결 실패 시에도 앱을 종료하지 않고 오류 상태를 JSON으로 반환합니다.

`/categories`, `/departments`는 활성화된 선택값만 `sort_order`, `id` 오름차순으로 반환합니다. PostgreSQL이 실행 중이지 않거나 테이블이 없으면 FastAPI 앱은 종료되지 않고 DB 오류 응답을 반환할 수 있습니다. 테이블이 비어 있으면 빈 배열 `[]`이 반환될 수 있습니다.

로컬 PostgreSQL에 migration이 적용된 뒤 테이블이 비어 있으면 `/categories`, `/departments`는 빈 배열 `[]`을 반환합니다. `python -m app.db.seed`를 수동 실행한 뒤에는 `/categories`, `/departments`에서 기본 선택값을 확인할 수 있습니다.

## Assets API

현재 제공 API:

- `GET /assets`: 삭제되지 않은 자산 목록 조회
- `GET /assets/{asset_id}`: 삭제되지 않은 자산 상세 조회
- `GET /assets/{asset_id}/history`: 삭제되지 않은 자산의 변경 이력 조회
- `POST /assets`: 신규 자산 등록
- `PUT /assets/{asset_id}`: 삭제되지 않은 자산 수정
- `PATCH /assets/{asset_id}/dispose`: 자산 폐기 상태 처리
- `DELETE /assets/{asset_id}`: 자산 soft delete 처리
- `GET /stats/summary`: 삭제되지 않은 자산의 현황 요약 조회

`GET /assets`는 `deleted_at IS NULL` 조건을 기본 적용하고, `status`, `category_id`, `department_id`, `keyword` query parameter를 지원합니다. `keyword`는 `name`, `model_name`, `serial_number`, `user_name`에서 검색합니다. 정렬은 `created_at DESC`, `id DESC` 기준입니다.

`GET /assets/{asset_id}/history`는 `deleted_at IS NULL`인 자산에 대해서만 변경 이력을 조회합니다. 자산이 없거나 soft delete된 자산이면 `404`를 반환합니다. 이력 정렬은 `changed_at DESC`, `id DESC` 기준입니다. soft deleted 자산의 history 조회는 추후 관리자 기능에서 별도로 구현합니다.

`POST /assets`는 `name`, `category_id`, `status`를 필수로 받습니다. `serial_number`는 nullable이며 입력 시 앞뒤 공백 제거 후 대문자로 변환하고 `A-Z`, `0-9`만 허용합니다. 삭제되지 않은 기존 자산과 시리얼번호가 중복되면 `409`를 반환합니다.

등록 성공 시 `asset_history`에 `등록` 이력 1건을 같은 트랜잭션에서 기록합니다. 등록 또는 이력 기록 실패 시 rollback합니다.

`PUT /assets/{asset_id}`는 보낸 필드 중 실제 변경된 필드만 수정하고 이력을 기록합니다. `status` 변경은 `상태변경`, 일반 필드 변경은 `수정` action type으로 기록합니다. 시리얼번호 중복 검사는 자기 자신을 제외하고 삭제되지 않은 다른 자산을 대상으로 수행합니다.

`PATCH /assets/{asset_id}/dispose`는 `deleted_at`을 건드리지 않고 `status`만 `폐기`로 변경합니다. 이미 폐기 상태인 자산은 추가 이력을 만들지 않고 현재 자산을 반환합니다.

`DELETE /assets/{asset_id}`는 실제 row를 삭제하지 않고 `deleted_at`에 현재 시각을 입력합니다. 삭제 처리 시 `asset_history`에 `삭제` 이력을 기록합니다. 이미 soft delete된 자산은 기본 조회 대상에서 제외되어 `404`를 반환합니다.

## Stats API

`GET /stats/summary`는 `deleted_at IS NULL`인 자산만 기준으로 요약 통계를 반환합니다.

응답 항목:

- `total_assets`: 전체 자산 수
- `in_use_assets`: 사용중 자산 수
- `unused_assets`: 미사용 자산 수
- `disposed_assets`: 폐기 자산 수
- `total_purchase_amount`: 총 구매금액

자산이 없으면 모든 값을 `0`으로 반환합니다. PostgreSQL 연결 실패 시 기존 API와 같이 `503`을 반환합니다.

아직 제공하지 않는 API:

- 전체 asset history 목록 조회 API
- soft deleted 자산 history 조회 관리자 API

## 로컬 Backend API 흐름 검증

아래 절차는 운영 NAS DB가 아닌 로컬 개발 PostgreSQL에서만 실행합니다. 기존 서버, 기존 서비스, SCM MySQL에는 접속하지 않습니다.

로컬 PostgreSQL 준비 예시:

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev"
```

기본 검증:

```powershell
cd backend
pip install -r requirements.txt
python -m compileall app
alembic --help
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8001
```

seed는 개발자가 직접 `python -m app.db.seed`를 실행할 때만 동작합니다. FastAPI 시작 시 자동 실행되지 않습니다.

API 확인 순서:

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8001/health/db
Invoke-RestMethod http://localhost:8001/categories
Invoke-RestMethod http://localhost:8001/departments
```

`GET /categories` 응답에서 존재하는 `id`를 골라 아래 `category_id`에 넣습니다. `departments`가 비어 있으면 `department_id`는 `null`로 둡니다.

자산 등록:

```powershell
$asset = Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8001/assets `
  -ContentType "application/json" `
  -Body '{
    "category_id": 1,
    "department_id": null,
    "name": "테스트 노트북",
    "model_name": "TEST-MODEL",
    "serial_number": "TEST12345",
    "purchase_date": null,
    "purchase_price": null,
    "user_name": "테스트사용자",
    "status": "미사용",
    "note": "로컬 개발 검증용"
  }'
```

자산 조회/수정/폐기/삭제/이력 확인:

```powershell
Invoke-RestMethod http://localhost:8001/assets
Invoke-RestMethod "http://localhost:8001/assets/$($asset.id)"

Invoke-RestMethod `
  -Method Put `
  -Uri "http://localhost:8001/assets/$($asset.id)" `
  -ContentType "application/json" `
  -Body '{"user_name":"수정사용자","note":"로컬 개발 수정 검증"}'

Invoke-RestMethod -Method Patch "http://localhost:8001/assets/$($asset.id)/dispose"
Invoke-RestMethod "http://localhost:8001/assets/$($asset.id)/history"
Invoke-RestMethod -Method Delete "http://localhost:8001/assets/$($asset.id)"
```

soft delete 후 기본 상세 조회는 `404`가 정상입니다. 현재 정책상 soft deleted 자산의 history 조회도 `404`입니다.

오류 케이스 확인:

```powershell
# 잘못된 serial_number: 422
Invoke-WebRequest `
  -Method Post `
  -Uri http://localhost:8001/assets `
  -ContentType "application/json" `
  -Body '{"category_id":1,"name":"오류 테스트","serial_number":"ABC-123","status":"미사용"}' `
  -SkipHttpErrorCheck

# 중복 serial_number: 409
Invoke-WebRequest `
  -Method Post `
  -Uri http://localhost:8001/assets `
  -ContentType "application/json" `
  -Body '{"category_id":1,"name":"중복 테스트","serial_number":"TEST12345","status":"미사용"}' `
  -SkipHttpErrorCheck

# 없는 asset_id 조회: 404
Invoke-WebRequest http://localhost:8001/assets/999999 -SkipHttpErrorCheck
```

PostgreSQL이 실행 중이지 않으면 `/assets`, `/categories`, `/departments` 등 DB 접근 API는 `503` JSON 오류를 반환할 수 있습니다. 이 경우에도 FastAPI 앱 자체가 종료되면 안 됩니다.

## 포트 기준

- Backend 개발 서버: `8001`
- Backend 배포 외부 포트: `8010`
- 포트 `80`, `8080`은 SCM 또는 NAS 내부 서비스와 충돌할 수 있으므로 사용하지 않습니다.
