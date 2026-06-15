# API

이 문서는 현재 준비된 자산관리 백엔드 API 기준입니다. Backend 개발 서버 포트는 `8001`입니다.

## GET /assets

삭제되지 않은 자산 목록을 조회합니다. 기본 조건은 `deleted_at IS NULL`입니다.

Query parameter:

- `status`: `사용중`, `미사용`, `폐기`
- `category_id`: 분류 ID
- `department_id`: 부서 ID
- `keyword`: `name`, `model_name`, `serial_number`, `user_name` 검색

정렬 기준:

- `created_at` 내림차순
- `id` 내림차순

응답 예시:

```json
[
  {
    "id": 1,
    "category_id": 1,
    "department_id": null,
    "department_name": null,
    "name": "업무용 노트북",
    "model_name": "ThinkPad",
    "serial_number": "ABC123",
    "purchase_date": null,
    "purchase_price": null,
    "user_name": null,
    "status": "미사용",
    "note": null,
    "created_at": "2026-06-11T00:00:00Z",
    "updated_at": "2026-06-11T00:00:00Z",
    "deleted_at": null
  }
]
```

PostgreSQL 연결 실패 또는 테이블 미준비 상태에서는 FastAPI 앱은 종료되지 않고 `503` DB 오류 응답을 반환할 수 있습니다.

## GET /assets/export/excel

삭제되지 않은 자산 목록을 엑셀 파일로 다운로드합니다. 기본 조건은 `deleted_at IS NULL`입니다.

Query parameter:

- `status`: `사용중`, `미사용`, `폐기`
- `category_id`: 분류 ID
- `department_id`: 부서 ID
- `department_name`: 부서명 또는 사용자명 검색
- `keyword`: `name`, `model_name`, `serial_number`, `department_name`, `user_name`, 부서 후보명 검색

다운로드 파일명:

- `asset_list_YYYY-MM-DD.xlsx`

엑셀 컬럼:

- `제품명`
- `상태`
- `분류`
- `시리얼번호`
- `부서(사용자명)`
- `구매일`
- `모델명`
- `메모`
- `등록일`

DB 연결 실패 시 `503`을 반환합니다.

## GET /assets/import/template

엑셀 일괄 등록용 업로드 양식을 다운로드합니다.

다운로드 파일명:

- `asset_import_template.xlsx`

양식 컬럼:

- `제품명`
- `분류`
- `부서(사용자명)`
- `상태`
- `시리얼번호`
- `메모`
- `구매일`
- `모델명`

## POST /assets/import/preview

엑셀 파일을 업로드해 각 행을 검증합니다. 이 API는 DB에 저장하지 않습니다.

검증 규칙:

- `제품명`, `분류`, `상태`는 필수입니다.
- `상태`는 `사용중`, `미사용`, `폐기`만 허용합니다.
- `분류`는 기존 활성 categories에 있는 이름만 허용합니다.
- `부서(사용자명)`은 자유 텍스트입니다.
- `시리얼번호`는 비어 있어도 됩니다. 값이 있으면 `A-Z`, `0-9`만 허용하며 대문자로 정규화합니다.
- 삭제되지 않은 기존 자산과 중복되는 시리얼번호는 오류입니다.
- 업로드 파일 안에서 중복되는 시리얼번호는 오류입니다.
- `구매일`은 비어 있거나 `YYYY-MM-DD` 형식이어야 합니다.

응답 예시:

```json
{
  "total_rows": 10,
  "valid_rows": 8,
  "error_rows": 2,
  "rows": [
    {
      "row_number": 2,
      "is_valid": true,
      "data": {
        "name": "테스트 노트북",
        "category_name": "노트북",
        "department_name": "총무팀 홍길동",
        "status": "사용중",
        "serial_number": "TEST001",
        "note": "테스트",
        "purchase_date": null,
        "model_name": null
      },
      "errors": []
    }
  ]
}
```

## POST /assets/import/commit

미리보기에서 정상 검증된 행만 일괄 등록합니다. 오류 행은 등록하지 않습니다.

등록 정책:

- 요청의 `rows` 중 `is_valid = true`이고 `data`가 있는 행만 처리합니다.
- 등록 시 기존 `POST /assets`와 같은 자산 생성 로직을 사용하므로 `asset_history`에 `등록` 이력이 남습니다.
- commit 시점에 분류 또는 시리얼번호 상태가 바뀐 행은 건너뛰고 오류 목록으로 반환합니다.
- DB 연결 실패 시 `503`을 반환합니다.

## GET /assets/{asset_id}

자산 ID 기준으로 삭제되지 않은 자산 상세를 조회합니다. `deleted_at`이 있는 자산은 기본적으로 조회하지 않습니다.

- 자산이 없으면 `404`를 반환합니다.
- DB 연결 실패 시 `503`을 반환합니다.

## GET /assets/{asset_id}/history

특정 자산의 변경 이력 목록을 조회합니다.

정렬 기준:

- `changed_at` 내림차순
- `id` 내림차순

응답 예시:

```json
[
  {
    "id": 1,
    "asset_id": 10,
    "action_type": "등록",
    "field_name": null,
    "old_value": null,
    "new_value": null,
    "memo": "자산 등록",
    "changed_at": "2026-06-11T10:00:00"
  },
  {
    "id": 2,
    "asset_id": 10,
    "action_type": "수정",
    "field_name": "user_name",
    "old_value": "홍길동",
    "new_value": "김철수",
    "memo": null,
    "changed_at": "2026-06-11T11:00:00"
  }
]
```

조회 정책:

- 기본은 `deleted_at IS NULL`인 자산만 history 조회가 가능합니다.
- 자산이 없거나 soft delete된 자산이면 `404`를 반환합니다.
- soft deleted 자산의 history 조회는 추후 관리자 기능에서 별도로 구현합니다.
- DB 연결 실패 시 `503`을 반환합니다.

## POST /assets

신규 자산을 등록합니다.

필수값:

- `name`
- `category_id`
- `status`

요청 예시:

```json
{
  "category_id": 1,
  "department_id": null,
  "department_name": "총무팀",
  "name": "업무용 노트북",
  "model_name": "ThinkPad",
  "serial_number": "abc123",
  "purchase_date": null,
  "purchase_price": null,
  "user_name": null,
  "status": "미사용",
  "note": null
}
```

`serial_number`는 nullable입니다. 값이 있으면 앞뒤 공백 제거 후 대문자로 변환하고, `A-Z`, `0-9`만 허용합니다. 한글, 공백, 특수문자는 허용하지 않습니다.

등록 전 삭제되지 않은 기존 자산 중 같은 `serial_number`가 있는지 검사합니다. 중복이면 `409`를 반환합니다.

등록 성공 시 `asset_history`에 `등록` 이력을 1건 기록합니다. 등록 또는 이력 기록 중 DB 오류가 나면 rollback 후 오류 응답을 반환합니다.

## PUT /assets/{asset_id}

삭제되지 않은 자산을 수정합니다. `deleted_at IS NULL`인 자산만 수정할 수 있습니다.

수정 가능 필드:

- `name`
- `category_id`
- `department_id`
- `department_name`
- `model_name`
- `serial_number`
- `purchase_date`
- `purchase_price`
- `user_name`
- `status`
- `note`

`serial_number` 검증 정책은 등록 API와 같습니다. 값이 있으면 앞뒤 공백 제거 후 대문자로 변환하고, `A-Z`, `0-9`만 허용합니다. 다른 삭제되지 않은 자산과 중복되면 `409`를 반환합니다.

변경된 필드만 `asset_history`에 기록합니다. `status` 변경은 `상태변경`, 그 외 일반 필드 변경은 `수정` action type으로 기록합니다. 수정 또는 이력 기록 중 DB 오류가 나면 rollback 후 오류 응답을 반환합니다.

## PATCH /assets/{asset_id}/dispose

자산을 실제 삭제하지 않고 `status`를 `폐기`로 변경합니다. `deleted_at`은 변경하지 않습니다.

- 자산이 없거나 이미 soft delete된 자산이면 `404`를 반환합니다.
- 이미 `폐기` 상태인 자산은 추가 이력을 만들지 않고 현재 자산을 그대로 반환합니다.
- 폐기 처리 시 `asset_history`에 `폐기` 이력을 기록합니다.

## DELETE /assets/{asset_id}

자산 row를 실제 삭제하지 않고 soft delete 처리합니다.

- `deleted_at`에 현재 시각을 입력합니다.
- `asset_history`에 `삭제` 이력을 기록합니다.
- 이미 soft delete된 자산은 기본 조회 대상에서 제외되므로 `404`를 반환합니다.
- 삭제 또는 이력 기록 중 DB 오류가 나면 rollback 후 오류 응답을 반환합니다.

## GET /categories

활성화된 자산 분류 선택값을 조회합니다.

정렬 기준:

- `sort_order` 오름차순
- `id` 오름차순

응답 예시:

```json
[
  {
    "id": 1,
    "name": "노트북",
    "sort_order": 10,
    "is_active": true
  },
  {
    "id": 2,
    "name": "데스크탑",
    "sort_order": 20,
    "is_active": true
  }
]
```

DB가 비어 있으면 빈 배열 `[]`이 반환될 수 있습니다. PostgreSQL 연결 실패 또는 테이블 미준비 상태에서는 FastAPI 앱은 종료되지 않고 DB 오류 응답을 반환할 수 있습니다.

로컬 개발 DB에서 첫 migration 적용 후 categories 테이블이 비어 있으면 `[]`이 반환됩니다. 개발자가 직접 `python -m app.db.seed`를 실행하면 기본 분류 후보가 추가되고 이 API에서 목록을 확인할 수 있습니다.

## GET /departments

활성화된 부서 후보값을 조회합니다. 자산 등록/수정 화면은 부서명을 직접 입력하며, 입력한 부서명이 기존 후보와 일치하면 호환용 `department_id`도 함께 저장할 수 있습니다. 신규/임의 부서명은 `assets.department_name`에 저장합니다.

정렬 기준:

- `sort_order` 오름차순
- `id` 오름차순

응답 예시:

```json
[
  {
    "id": 1,
    "name": "총무팀",
    "sort_order": 10,
    "is_active": true
  },
  {
    "id": 2,
    "name": "영업팀",
    "sort_order": 20,
    "is_active": true
  }
]
```

DB가 비어 있으면 빈 배열 `[]`이 반환될 수 있습니다. 회사 실제 부서명은 하드코딩하지 않으며 운영 단계에서 별도로 등록합니다.

로컬 개발 DB에서 첫 migration 적용 후 departments 테이블이 비어 있으면 `[]`이 반환됩니다. 개발자가 직접 `python -m app.db.seed`를 실행하면 기본 부서 후보가 추가되고 이 API에서 목록을 확인할 수 있습니다.

## GET /stats/summary

삭제되지 않은 자산 기준의 현황 요약을 조회합니다. `deleted_at IS NULL` 조건을 적용하며, soft delete된 자산은 전체 자산 수와 총 구매금액에서 제외합니다.

응답 예시:

```json
{
  "total_assets": 10,
  "in_use_assets": 7,
  "unused_assets": 2,
  "disposed_assets": 1,
  "total_purchase_amount": 12340000
}
```

집계 기준:

- `total_assets`: 삭제되지 않은 전체 자산 수
- `in_use_assets`: `status = "사용중"`인 자산 수
- `unused_assets`: `status = "미사용"`인 자산 수
- `disposed_assets`: `status = "폐기"`인 자산 수
- `total_purchase_amount`: 삭제되지 않은 자산의 `purchase_price` 합계, `NULL`은 `0`으로 처리

데이터가 없으면 모든 값을 `0`으로 반환합니다. DB 연결 실패 시 `503`을 반환합니다.

Frontend 요약 카드는 이 응답 중 `total_purchase_amount`를 표시하지 않고 전체 자산, 사용중, 미사용, 폐기 4개 카드만 표시합니다. Backend 응답 필드는 하위 호환을 위해 유지합니다.

## GET /stats/by-category

삭제되지 않은 자산을 분류명별로 집계합니다. `deleted_at IS NULL` 조건을 적용합니다.

응답 예시:

```json
[
  {
    "category_name": "노트북",
    "asset_count": 5
  }
]
```

집계 기준:

- `category_name`: 자산 분류명
- `asset_count`: 해당 분류의 삭제되지 않은 자산 수

데이터가 없으면 빈 배열 `[]`을 반환합니다. DB 연결 실패 시 `503`을 반환합니다.

## GET /stats/monthly

최근 3개월 기준 월별 등록 수와 폐기 수를 조회합니다.

응답 예시:

```json
[
  {
    "month": "2026-06",
    "registered_count": 5,
    "disposed_count": 1
  }
]
```

집계 기준:

- `month`: `YYYY-MM`
- `registered_count`: `assets.created_at` 기준 등록 수, `deleted_at IS NULL` 자산만 집계
- `disposed_count`: `asset_history`의 `폐기` 또는 `상태변경 -> 폐기` 이력 기준 폐기 수. 폐기 이력이 없는 기존 폐기 상태 자산은 `updated_at` 월로 보완 집계

최근 3개월은 데이터가 없는 월도 `0`으로 반환합니다. DB 연결 실패 시 `503`을 반환합니다.

## GET /stats/by-department

삭제되지 않은 자산을 부서명별로 집계합니다. `deleted_at IS NULL` 조건을 적용합니다. `department_name`이 있으면 해당 값을 우선 사용하고, 없으면 기존 `department_id`의 부서명을 사용합니다. 둘 다 없으면 `부서 미지정`으로 집계합니다.

응답 예시:

```json
[
  {
    "department_name": "총무팀",
    "asset_count": 5
  }
]
```

집계 기준:

- `department_name`: 자산 부서명, 없으면 `부서 미지정`
- `asset_count`: 해당 부서의 삭제되지 않은 자산 수

데이터가 없으면 빈 배열 `[]`을 반환합니다. DB 연결 실패 시 `503`을 반환합니다.

## 로컬 개발 DB 검증 절차

운영 NAS DB가 아닌 로컬 개발 PostgreSQL에서만 실행합니다.

```powershell
cd backend
pip install -r requirements.txt
python -m compileall app
alembic --help
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8001
```

확인 URL:

- http://localhost:8001/health
- http://localhost:8001/health/db
- http://localhost:8001/assets
- http://localhost:8001/assets/1
- http://localhost:8001/assets/1/history
- http://localhost:8001/categories
- http://localhost:8001/departments
- http://localhost:8001/stats/summary
- http://localhost:8001/stats/by-category
- http://localhost:8001/stats/by-department
- http://localhost:8001/stats/monthly
- http://localhost:8001/docs

선택 seed:

```powershell
cd backend
python -m app.db.seed
```

seed 명령은 개발자가 직접 실행할 때만 동작하며 앱 시작 시 자동 실행되지 않습니다.

## 전체 Backend API 흐름 검증

운영 NAS DB가 아닌 로컬 개발 PostgreSQL에서만 실행합니다. 포트는 backend 개발 포트 `8001`을 사용하며 `80`, `8080`은 사용하지 않습니다. 삭제 검증은 새로 만든 검증용 자산에 대해서만 수행하며, 실제 운영 데이터 삭제 명령은 사용하지 않습니다.

1. `alembic upgrade head`로 로컬 개발 DB에 migration을 적용합니다.
2. `python -m app.db.seed`를 개발자가 직접 실행해 기본 categories/departments 후보를 넣습니다.
3. `GET /health`로 backend 상태를 확인합니다.
4. `GET /categories`에서 실제 존재하는 `category_id`를 확인합니다.
5. `GET /departments`에서 부서명 입력 후보를 확인합니다. 비어 있어도 자산의 `department_name`은 직접 입력할 수 있습니다.
6. `GET /assets`로 목록 조회를 확인합니다.
7. `GET /stats/summary`로 전체/상태별 수량을 확인합니다.
8. `GET /stats/by-category`로 분류별 자산 수를 확인합니다.
9. `GET /stats/by-department`로 부서별 자산 수를 확인합니다.
10. `GET /stats/monthly`로 최근 3개월 등록/폐기 수를 확인합니다.
11. `POST /assets`로 검증용 자산을 등록합니다.
12. `GET /stats/summary`에서 전체 자산 수가 증가하는지 확인합니다.
13. `GET /stats/by-category`에서 해당 분류 자산 수가 증가하는지 확인합니다.
14. `GET /stats/by-department`에서 해당 부서 자산 수가 증가하는지 확인합니다.
15. `GET /stats/monthly`에서 현재 월 등록 수가 증가하는지 확인합니다.
16. `GET /assets/{asset_id}`로 상세 조회를 확인합니다.
17. `PUT /assets/{asset_id}`로 필드 변경과 history 기록을 확인합니다.
18. `GET /assets/{asset_id}/history`로 이력 정렬과 내용을 확인합니다.
19. `PATCH /assets/{asset_id}/dispose`로 폐기 상태 변경을 확인합니다.
20. `GET /stats/summary`에서 폐기 자산 수가 증가하는지 확인합니다.
21. `GET /stats/monthly`에서 현재 월 폐기 수가 증가하는지 확인합니다.
22. `DELETE /assets/{asset_id}`로 검증용 자산 soft delete를 확인합니다.
23. `GET /stats/summary`, `GET /stats/by-category`, `GET /stats/by-department`에서 soft delete된 자산이 집계에서 제외되는지 확인합니다.
24. soft delete 후 `GET /assets/{asset_id}`는 `404`가 정상입니다.

검증용 등록 요청:

```json
{
  "category_id": 1,
  "department_id": null,
  "department_name": "전산팀",
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

오류 케이스 기대값:

- 잘못된 `serial_number` `ABC-123`: `422`
- 중복 `serial_number`: `409`
- 없는 `asset_id` 조회: `404`
- DB 미연결 상태: `503`
- soft delete 후 기본 상세 조회: `404`
- soft delete 후 기본 history 조회: 현재 정책상 `404`

## 운영 원칙

- seed 데이터는 앱 시작, migration 실행 중 자동 insert하지 않습니다.
- 실제 운영 DB에는 아직 적용하지 않습니다.
- 기존 서버, 기존 서비스, 기존 SCM, 기존 MySQL은 건드리지 않습니다.
- 포트 `80`, `8080`은 사용하지 않습니다.
- 이번 단계에서는 assets 목록, 상세, 등록, 수정, 폐기, soft delete, 자산별 history 조회 API, categories/departments 조회 API, 자산 요약/분류별/부서별/월별 통계 API를 제공합니다.
- 전체 asset history 목록 조회 API와 soft deleted 자산 history 조회 관리자 API는 제공하지 않습니다.

## Frontend 연동 기준

React frontend는 `VITE_API_BASE_URL`을 사용해 Backend API를 호출합니다. 값이 없으면 `http://127.0.0.1:8001`을 기본값으로 사용합니다.

로컬 개발 CORS 허용 origin:

- `http://127.0.0.1:5173`
- `http://localhost:5173`

브라우저에서 `GET /health`, `GET /health/db`, `GET /categories`, `GET /departments`, `GET /assets`, `GET /stats/summary`, `GET /stats/by-category`, `GET /stats/by-department`, `GET /stats/monthly`가 CORS 오류 없이 호출되어야 합니다.

현재 frontend 화면:

- 제목 카드 우측의 작은 Backend/DB 상태 표시와 상태 확인 버튼
- `GET /stats/summary` 기반 자산 현황 요약 카드
- `GET /stats/by-category` 기반 분류별 자산 통계 카드
- `GET /stats/by-department` 기반 부서별 자산 통계 카드
- `GET /stats/monthly` 기반 월별 등록/폐기 추이
- `GET /assets` 기반 자산 목록
- 자산 목록 행/카드 클릭 시 상세보기 모달
- 상세보기 모달 안의 `GET /assets/{asset_id}` 기반 자산 상세
- 상세보기 모달 안의 `GET /assets/{asset_id}/history` 기반 자산 변경 이력
- 검색어, 상태, 분류, 부서 필터와 필터 초기화
- Backend 기본 정렬은 최신 등록순이며, frontend에서 제품명/상태/사용자/시리얼번호 클릭 정렬을 제공합니다.
- `GET /categories` 기반 분류 선택값
- `GET /departments` 기반 부서명 입력 후보값
- `POST /assets` 기반 자산 등록
- `PUT /assets/{asset_id}` 기반 자산 수정
- `PATCH /assets/{asset_id}/dispose` 기반 자산 폐기 처리
- `DELETE /assets/{asset_id}` 기반 자산 soft delete

Backend가 꺼져 있거나 PostgreSQL이 준비되지 않아 API가 `503`을 반환해도 화면 전체가 깨지지 않고 오류 메시지를 표시합니다. 변경 이력 조회 실패는 상세 화면 전체가 아니라 이력 영역에만 오류를 표시합니다. `serial_number` 검증 오류 `422`, 중복 오류 `409`는 등록/수정 폼의 오류 메시지 영역에 표시합니다. 폐기/삭제 실패 메시지는 상세 패널의 오류 영역에 표시합니다.
