# Local DB Setup

이 문서는 5-9단계 로컬 PostgreSQL 개발 DB 연결, Alembic migration, seed 데이터 등록, 실제 API CRUD 검증 절차입니다. 운영 NAS DB, 기존 서버/서비스, SCM MySQL에는 접속하지 않습니다. 포트 `80`, `8080`은 사용하지 않습니다.

## 1. PostgreSQL 설치 확인

PowerShell에서 PostgreSQL 17 클라이언트를 확인합니다.

```powershell
"C:\Program Files\PostgreSQL\17\bin\psql.exe" --version
```

## 2. DB 접속 확인

개발용 DB `asset_manager_dev`에 접속합니다.

```powershell
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d asset_manager_dev
```

접속 후 테이블 확인은 migration 적용 뒤에 실행합니다.

```sql
\dt
SELECT id, name, sort_order, is_active FROM categories ORDER BY sort_order, id;
SELECT id, name, sort_order, is_active FROM departments ORDER BY sort_order, id;
```

## 3. backend/.env 생성

실제 비밀번호가 들어가는 `backend/.env`는 GitHub에 올리지 않습니다. `backend/.env.example`을 참고해 로컬 PC에서만 `backend/.env`를 직접 만듭니다.

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev
```

`YOUR_LOCAL_PASSWORD`에는 로컬 PostgreSQL `postgres` 계정 비밀번호를 넣습니다. 문서나 코드에는 실제 비밀번호를 저장하지 않습니다.

현재 backend 의존성은 `psycopg[binary]`를 사용하므로 URL 드라이버는 `postgresql+psycopg`를 기준으로 합니다. `psycopg2`는 추가하지 않습니다.

## 3-1. 실제 실행 순서

1. 사용자가 직접 `backend/.env`를 생성합니다.
2. backend 가상환경을 활성화합니다.
3. `pip install -r requirements.txt`를 실행합니다.
4. `python -m compileall app`로 Python 문법을 확인합니다.
5. `alembic upgrade head`로 migration을 적용합니다.
6. `python -m app.db.seed`로 기본 선택값을 등록합니다.
7. `uvicorn app.main:app --reload --host 127.0.0.1 --port 8001`로 backend를 실행합니다.
8. `cd frontend` 후 `npm run dev`로 frontend를 실행합니다.
9. 브라우저에서 실제 화면과 API 동작을 검증합니다.

## 4. Alembic Migration 실행

Alembic은 `backend` 폴더 기준으로 실행합니다. `backend/alembic/env.py`가 `app.core.config.settings.database_url`을 읽으므로 backend와 같은 `DATABASE_URL`을 사용합니다.

실행 전 체크리스트:

- `backend/.env`를 사용자가 직접 만들었고 Git에 올리지 않습니다.
- `DATABASE_URL`이 `postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev` 형식입니다.
- 실제 비밀번호를 문서나 코드에 기록하지 않았습니다.
- PostgreSQL 17 서비스가 실행 중입니다.
- `asset_manager_dev` DB가 존재합니다.
- backend 가상환경이 활성화되어 있고 `pip install -r requirements.txt`가 완료되었습니다.
- 운영 NAS DB, 기존 SCM MySQL, 기존 서버에는 접속하지 않습니다.

```powershell
cd backend
.venv\Scripts\activate
alembic upgrade head
alembic current
```

## 5. Seed 데이터 등록

기본 categories/departments 후보는 개발자가 직접 명령을 실행할 때만 등록됩니다. 앱 시작이나 migration 중 자동 실행되지 않습니다.

실행 전 체크리스트:

- `alembic upgrade head`가 로컬 `asset_manager_dev`에 성공했습니다.
- `APP_ENV=development`입니다.
- `APP_ENV=production`이 아닌 상태임을 확인했습니다.
- seed 대상은 기본 categories/departments 후보뿐입니다.
- 같은 이름이 이미 있으면 중복 insert하지 않는 구조입니다.
- 운영 NAS DB나 기존 SCM MySQL에 연결하지 않습니다.
- `DROP`, `TRUNCATE` 등 실제 데이터를 삭제하는 명령을 사용하지 않습니다.

```powershell
cd backend
.venv\Scripts\activate
python -m app.db.seed
```

`APP_ENV=production`이면 seed 명령은 실행을 거부합니다. 이미 같은 이름의 category/department가 있으면 중복 insert하지 않습니다.

## 6. Backend 실행

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

확인 URL:

- http://127.0.0.1:8001/health
- http://127.0.0.1:8001/docs

로컬 개발 CORS 허용 origin:

- `http://127.0.0.1:5173`
- `http://localhost:5173`

브라우저 Console에서 CORS 오류가 보이면 backend 개발 서버가 최신 코드로 재시작되었는지 확인합니다.

## 7. Frontend 실행

```powershell
cd frontend
npm run dev
```

확인 URL:

- http://127.0.0.1:5173/

Frontend 화면에서 다음 API 호출이 CORS 오류 없이 완료되는지 확인합니다.

- `GET /health`
- `GET /health/db`
- `GET /categories`
- `GET /departments`
- `GET /assets`

## 8. 실제 API CRUD 검증 흐름

아래 순서로 Swagger UI 또는 PowerShell `Invoke-RestMethod`에서 확인합니다. 삭제 검증은 새로 만든 검증용 자산에 대해서만 수행하며, 실제 운영 데이터 삭제 명령은 사용하지 않습니다.

1. `GET /health`
2. `GET /categories`
3. `GET /departments`
4. `GET /assets`
5. `POST /assets` 자산 등록
6. `GET /assets/{asset_id}` 상세 조회
7. `PUT /assets/{asset_id}` 수정
8. `GET /assets/{asset_id}/history` 변경 이력 조회
9. `PATCH /assets/{asset_id}/dispose` 폐기 처리
10. `DELETE /assets/{asset_id}` 검증용 자산 soft delete
11. 삭제 후 `GET /assets/{asset_id}`가 `404` 처리되는지 확인

검증용 등록 payload 예시:

```json
{
  "category_id": 1,
  "department_id": 1,
  "name": "테스트 노트북",
  "model_name": "TEST-MODEL",
  "serial_number": "TEST12345",
  "purchase_date": null,
  "purchase_price": null,
  "user_name": "테스트사용자",
  "status": "미사용",
  "note": "로컬 개발 검증용"
}
```

오류 검증:

- DB 연결 실패 시 DB 접근 API는 `503`
- 없는 `asset_id` 조회 시 `404`
- 잘못된 `serial_number` 입력 시 `422`
- 중복 `serial_number` 입력 시 `409`
- 삭제된 자산 상세 조회 시 `404`

## 9. 검증 명령어 모음

Backend:

```powershell
cd backend
python -m compileall app
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd frontend
npm run build
npm run dev
```

## 10. 금지 사항

- 실제 `backend/.env`를 생성하거나 커밋하지 않습니다.
- 실제 DB 비밀번호를 코드/문서에 고정하지 않습니다.
- 운영 NAS DB에 접속하지 않습니다.
- 기존 서버/서비스/SCM/MySQL을 건드리지 않습니다.
- 기존 SCM MySQL에 연결하지 않습니다.
- 포트 `80`, `8080`을 사용하지 않습니다.
- Docker/NAS 배포를 진행하지 않습니다.
- 실제 DB 데이터를 삭제하지 않습니다.
- 기본 흐름에 `DROP DATABASE`, `DROP TABLE`, `TRUNCATE`를 사용하지 않습니다.
