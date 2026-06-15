# DB Schema

이 문서는 자산관리 전용 PostgreSQL 기준의 초기 DB 설계입니다. 현재 SQLAlchemy 모델, Pydantic 스키마, Alembic 첫 마이그레이션 파일을 준비했고, 로컬 개발 DB에서만 migration 적용 검증을 진행합니다. 실제 운영 DB에는 테이블을 생성하지 않습니다.

## 원칙

- 기존 SCM MySQL DB와 연결하지 않습니다.
- 기존 서버, 기존 서비스, 기존 NAS 서비스 설정을 변경하지 않습니다.
- 자산관리 전용 PostgreSQL을 별도로 운영합니다.
- 포트 `80`, `8080`은 사용하지 않습니다.
- PostgreSQL은 컨테이너 내부 `5432`를 사용하며 외부 포트 매핑 없이 backend 컨테이너에서 접근하는 구성을 우선합니다.

## 테이블 목록

- `assets`: 자산 본체
- `asset_history`: 자산 변경 이력
- `categories`: 자산 분류
- `departments`: 사용 부서

## assets

자산 본체 테이블입니다. 기본키는 정수형 `id`를 사용합니다. 사내 업무 시스템에서 사람이 식별하고 관리하기 쉬운 단순 구조를 우선했고, 외부 공개 식별자가 필요해지면 별도 UUID 컬럼을 추가할 수 있습니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 정수형 기본키 |
| `category_id` | `categories.id` 참조, 필수 |
| `department_id` | `departments.id` 참조, nullable |
| `name` | 제품명, 필수 |
| `model_name` | 모델명 |
| `serial_number` | 시리얼번호, nullable |
| `purchase_date` | 구매일 |
| `purchase_price` | 구매금액 |
| `user_name` | 사용자명 |
| `status` | `사용중`, `미사용`, `폐기` |
| `note` | 메모 |
| `created_at` | 생성일시 |
| `updated_at` | 수정일시 |
| `deleted_at` | 삭제일시, soft delete 확장 대비 |

## asset_history

자산 변경 이력 테이블입니다. 이번 단계에서는 구조만 준비하고 실제 기록 로직은 구현하지 않습니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 정수형 기본키 |
| `asset_id` | `assets.id` 참조 |
| `action_type` | `등록`, `수정`, `상태변경`, `폐기`, `삭제` |
| `field_name` | 변경 항목 |
| `old_value` | 이전 값 |
| `new_value` | 변경 값 |
| `memo` | 메모 |
| `changed_at` | 변경일시 |

## categories

자산 분류 테이블입니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 정수형 기본키 |
| `name` | 분류명 |
| `sort_order` | 정렬 순서 |
| `is_active` | 사용 여부 |
| `created_at` | 생성일시 |
| `updated_at` | 수정일시 |

기본 분류 후보:

- 노트북
- 데스크탑
- 모니터
- 프린터
- 태블릿
- 휴대폰
- 키보드
- 마우스
- 충전기
- 허브
- 네트워크장비
- 기타전자기기

seed 후보는 `backend/app/db/seed_data.py`에도 상수로 정리했습니다. 이 파일은 실행 스크립트가 아니며 실제 DB insert를 수행하지 않습니다.

로컬 개발 DB에서 기본 분류 후보를 넣고 싶다면 개발자가 직접 다음 명령을 실행합니다.

```powershell
cd backend
python -m app.db.seed
```

이 명령은 migration 또는 FastAPI 앱 시작과 연결되어 있지 않습니다. `APP_ENV=production`에서는 실행을 거부합니다.

조회 API `GET /categories`는 `is_active = true`인 항목만 `sort_order`, `id` 오름차순으로 반환합니다. 이번 단계에서는 조회 API만 제공하며 생성, 수정, 삭제 API는 만들지 않습니다.

## departments

사용 부서 테이블입니다. 실제 부서명은 회사 운영 기준에 따라 달라질 수 있으므로 운영 단계에서 조정할 수 있습니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 정수형 기본키 |
| `name` | 부서명 |
| `sort_order` | 정렬 순서 |
| `is_active` | 사용 여부 |
| `created_at` | 생성일시 |
| `updated_at` | 수정일시 |

예시 부서 후보:

- 총무
- 경영지원
- 영업
- 개발
- 생산

기본 부서 seed 후보:

- 총무
- 경영지원
- 영업
- 개발
- 생산

로컬 개발 DB에서 기본 부서 후보를 넣고 싶다면 개발자가 직접 다음 명령을 실행합니다.

```powershell
cd backend
python -m app.db.seed
```

이 명령은 migration 또는 FastAPI 앱 시작과 연결되어 있지 않습니다. `APP_ENV=production`에서는 실행을 거부합니다.

조회 API `GET /departments`는 `is_active = true`인 항목만 `sort_order`, `id` 오름차순으로 반환합니다. 이번 단계에서는 조회 API만 제공하며 생성, 수정, 삭제 API는 만들지 않습니다.

## 상태값 기준

- `사용중`: 현재 사용자가 사용 중인 자산
- `미사용`: 창고 또는 부서 보관 중이며 아직 보유 중인 자산
- `폐기`: 더 이상 사용하지 않는 자산

## 삭제와 폐기의 차이

`폐기`는 실제 자산의 생명주기 상태입니다. 더 이상 사용하지 않지만 기록은 보존합니다.

`삭제`는 잘못 입력한 데이터를 제거하기 위한 관리 행위입니다. 향후 soft delete 정책을 적용할 수 있도록 `assets.deleted_at`을 nullable 컬럼으로 준비했습니다.

## 시리얼번호 정책

- 시리얼번호는 필수값이 아닙니다.
- 입력된 경우 영어 대문자 `A-Z`와 숫자 `0-9`만 허용할 예정입니다.
- 소문자 입력 시 저장 전 대문자로 변환할 예정입니다.
- 한글, 공백, 특수문자는 허용하지 않을 예정입니다.

현재 Pydantic 스키마에는 대문자 변환만 준비했습니다. 정규식 검증과 중복 검사는 CRUD/service 구현 단계에서 정책을 확정한 뒤 적용합니다.

## 중복 방지 정책

PostgreSQL의 일반 `UNIQUE` 제약은 nullable 컬럼 처리와 soft delete 정책을 함께 고려해야 합니다.

가능한 방식:

- DB 제약: `serial_number IS NOT NULL AND deleted_at IS NULL` 조건의 partial unique index를 사용하면 데이터 무결성이 강합니다.
- 서비스 레벨 검사: 사용자에게 더 친절한 오류 메시지를 줄 수 있지만 동시 등록 상황에서는 DB 제약보다 약합니다.

권장 방향은 서비스 레벨 사전 검사와 PostgreSQL partial unique index를 함께 사용하는 방식입니다. 다만 이번 단계의 첫 migration에는 serial number partial unique index를 넣지 않습니다. 4-3 또는 4-4 CRUD/service 단계에서 서비스 레벨 중복 검사를 먼저 구현하고, 동시 등록까지 DB에서 강제할 필요가 확정되면 별도 migration으로 partial unique index를 추가합니다.

partial unique index 장점:

- `serial_number IS NOT NULL AND deleted_at IS NULL` 조건으로 활성 자산의 중복을 DB가 강하게 차단할 수 있습니다.
- 동시 등록 상황에서도 데이터 무결성을 지킬 수 있습니다.

partial unique index 단점:

- 사용자가 이해하기 쉬운 오류 메시지는 별도 서비스 레벨 처리가 필요합니다.
- soft delete 복구 정책과 시리얼번호 재사용 정책을 먼저 확정해야 합니다.
- 이미 중복 데이터가 있는 운영 DB에는 index 생성 전 정리가 필요합니다.

## Alembic 마이그레이션

Alembic 설정은 `backend` 기준입니다.

- 설정 파일: `backend/alembic.ini`
- 환경 파일: `backend/alembic/env.py`
- 첫 migration: `backend/alembic/versions/20260611_0001_create_asset_tables.py`

첫 migration 준비 대상:

- `categories`
- `departments`
- `assets`
- `asset_history`
- enum 타입 `asset_status`
- enum 타입 `asset_action_type`

첫 migration에는 FK 관계, 기본 인덱스, `created_at`/`updated_at` 서버 기본값, `deleted_at` nullable 컬럼이 포함됩니다. `serial_number`는 nullable이며 일반 index만 포함하고 unique 제약은 보류합니다.

`alembic upgrade head`는 로컬 개발 DB에서만 수동 실행하세요. 실제 NAS 운영 DB에는 이번 단계에서 적용하지 않습니다. 실제 NAS 운영 DB 반영은 별도 배포 단계에서 백업 후 진행해야 합니다.

## 로컬 개발 DB 적용 검증

운영 NAS DB가 아닌 로컬 개발 PostgreSQL에서만 다음 절차를 사용합니다.

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/asset_manager_dev"
pip install -r requirements.txt
alembic --help
alembic upgrade head
alembic current
```

테이블 생성 확인 대상:

- `categories`
- `departments`
- `assets`
- `asset_history`

`psql` 사용 가능 시 확인 예시:

```sql
\dt
SELECT id, name, sort_order, is_active FROM categories ORDER BY sort_order, id;
SELECT id, name, sort_order, is_active FROM departments ORDER BY sort_order, id;
```

테이블만 생성되고 seed를 실행하지 않았다면 `GET /categories`, `GET /departments`는 빈 배열 `[]`을 반환할 수 있습니다. 기본 분류 후보가 필요할 때만 `python -m app.db.seed`를 수동 실행합니다.

Backend API 전체 흐름 검증은 `backend/README.md`와 `docs/API.md`의 로컬 개발 DB 검증 절차를 따릅니다. 운영 NAS DB에서는 `alembic upgrade head`, `python -m app.db.seed`, 검증용 자산 등록 요청을 실행하지 않습니다.
