# 신규 SCM 간극·위험·4-2 개발 우선순위

2026-10-27 기준. 코드 근거: `frontend/src/App.jsx`, `SettingsManagement.jsx`, `SettingsStage12.jsx`, `SettingsExtended.jsx`, `contexts/AuthContext.jsx`, `services/*`, `backend/app/main.py`, `backend/app/db/database.py`. DB 근거: [실측 카탈로그](SCM_DB_CATALOG.md). 본 문서는 설계 판단과 미검증 항목을 구분한다. DB 데이터 수정·마이그레이션·서버 재시작은 하지 않았다.

## 집계

| 항목 | 결과 |
|---|---:|
| 상단 메뉴 | 15개(표시 12, 숨김 3) |
| 하위 메뉴 | 28개(매장 5, 고객상담 9, 설정 14) |
| 표시 메뉴 고유 경로 | 39개(실제 화면/안내 38, 404 1) |
| 매핑 확신도 | 확정 24, 유력 8, 추정 6, 미확인 1 |
| 실제 업무 API 연결이 필요한 화면 | 38개; 연결 완료 0개 |
| 설계한 업무 API | 115개: GET 48(읽기), POST 47 + PATCH 18 + DELETE 2(쓰기 67) |
| 인증 필요한 업무 API | 114개; `POST /auth/login`만 공개. 현재 권한 구현은 없음 |
| DB 실측 | 업무 51개 + `alembic_version` 1개, 718컬럼, 259제약, 282인덱스, 버전 `20260729_0012` |
| ORM 모델 설계 대상 | 51개; 실제 모델 파일 0개 |

메뉴별 API 수는 **주 소유 영역에 한 번씩** 배정했다. 화면이 공유하는 `/customers`, `/sales` 등을 각 화면마다 중복 집계하지 않는다.

| 주 소유 영역 | API 수 | 읽기/쓰기 |
|---|---:|---:|
| 인증 | 3 | 1/2 |
| 사용자·계정 | 5 | 2/3 |
| 매장 | 4 | 2/2 |
| 직원 | 5 | 2/3 |
| 마켓 | 3 | 1/2 |
| 공통코드 | 6 | 2/4 |
| 시스템 설정 | 2 | 1/1 |
| 고객 | 6 | 3/3 |
| 상담 | 6 | 2/4 |
| A/S | 6 | 2/4 |
| A/S 증상·부품 | 6 | 2/4 |
| 상품 | 4 | 2/2 |
| 판매·결제 | 6 | 2/4 |
| 발주 | 5 | 2/3 |
| 입고 | 4 | 2/2 |
| 재고·시리얼 조회 | 3 | 3/0 |
| 매장 간 이동 | 3 | 1/2 |
| 재고 조정 | 3 | 1/2 |
| 물류·배송 | 6 | 2/4 |
| 공지 | 5 | 2/3 |
| 메모 | 4 | 1/3 |
| SMS 템플릿·로그·미리보기·수신거부 | 8 | 3/5 |
| 배치 | 3 | 2/1 |
| 시리얼 일괄 수정 | 6 | 2/4 |
| HOME·매장 통계·감사조회 | 3 | 3/0 |
| **합계** | **115** | **48/67** |

> `POST /sms/dry-run`은 HTTP method는 POST지만 외부 발송/DB 변경 없이 미리보기만 수행한다. 위 보수적 집계는 method 기준 쓰기 67에 포함한다. 실제 DB 쓰기 예정은 66개다. `POST /auth/logout`의 세션 저장소는 아직 결정되지 않았다.

## P0 — 인증·권한·데이터 보호

1. **Mock 사용자 제거 계획**: `AuthContext.jsx`는 고정 `CURRENT_USER_MOCK`, `authService.js`는 로그인/복원 stub이다. `permissions.js`는 활성 계정이면 대부분 메뉴/행위를 허용하고 설정만 admin으로 막는다. 서버는 현재 업무 라우터가 없어 인증·권한 검사가 없다. `users`의 실제 `username,password_hash,account_type,status`를 기반으로 로그인/세션/API 권한/매장 범위를 서버에서 구현해야 한다. 비밀번호 해시 알고리즘·저장 데이터 호환성은 스키마에서 확인할 수 없어 별도 검증 필요. `login_logs`와 `audit_logs`를 활용하되 감사 내용의 개인정보/비밀값을 제외한다.
2. **DB 역할 분리**: 현재 `new_scm_ro`/`backend/app/db/database.py` 연결은 읽기 전용 진단에 적합하다. 4-2 업무 쓰기용 계정·세션을 별도 최소 권한으로 설계한다. 현 단계에서 권한 변경이나 쓰기 연결은 하지 않았다.
3. **유일성 위험 재판정**: `customers.customer_code`, `products.product_code`, `sales.sale_code`, `as_requests.as_code`, `serial_inventories.serial_number`에는 모두 실제 unique index가 있다. 1단계의 “유일 제약 부재” 가정은 현 DB에 적용되지 않는다. 다만 공백/대소문자/전화 정규화, 코드 발급 충돌, soft delete 후 코드 재사용 정책은 여전히 필요하다. `goods_receipt_items`/`logistics_items`/`stock_transfer_items`의 시리얼 unique는 각각 부모 ID와 묶여 있어 **전역 시리얼 일관성**은 `serial_inventories`와 트랜잭션으로 확인해야 한다.
4. **조회 권한**: 고객 연락처·주소, 판매 결제, SMS 해시, 감사 before/after 데이터에 필드별 마스킹과 매장별 범위가 필요하다. `GET`도 무조건 허용하면 안 된다. 첨부/Excel의 다운로드 권한과 보존 기간을 확정해야 한다.

## P1 — 기준정보·핵심 업무

1. **화면과 API 차이**: 38개 화면/안내 중 업무 데이터가 백엔드에 연결된 화면은 0개. 고객/발주/메모 화면은 검색 입력과 빈 상태만 있다. `SettingsStage12`의 호출은 `settingsApiConfigured=false`, 서비스 메서드는 예외 stub이다. `SettingsManagement`의 계정/코드/배치 seed 로직은 실제 렌더된 하위 컴포넌트에 의해 가려진다. UI 존재를 기능 완료로 간주하지 않는다.
2. **재고 원자성**: `inventory_balances`는 `(store_id,product_id)` unique 및 잔량 비음수 CHECK가 있지만, `inventory_movements`와 잔량의 **합계 일치**를 DB 제약만으로 보장하지 않는다. 입고·출고·이동·조정은 행 잠금, 원장 추가, 잔량 갱신, 상태 이력을 같은 트랜잭션으로 처리한다. 원장 `source_type/source_id`는 실제 FK가 아니므로 참조 검증과 재처리 방지가 필요하다.
3. **판매/A/S/물류 연결**: `logistics_orders.source_sale_id`, `source_as_request_id` 실제 FK와 각각 partial unique index가 있다. 각 원천당 물류 1건 제약이 부분배송/재배송과 맞는지 확인한다. `source_type`과 해당 FK가 논리적으로 일치하도록 API 검증한다. `as_requests.source_consultation_id`도 unique여서 상담당 A/S 하나다. 반품·교환의 원판매/환불·대체품 관계는 확인되지 않았다.
4. **상태/삭제**: 상태별 CHECK와 일부 전용 이력 테이블은 확인됐다. 실제 전이 허용표, 취소 후 복구, 결제 취소, 입고 취소의 역분개, hard/soft delete 및 보존 기간은 미정이다. CHECK는 상태 전이를 검증하지 않는다. 이력 없는 상담·입고는 감사 로그로 충분한지 검토한다.
5. **인덱스**: 282개 인덱스가 있지만 모든 FK 열을 선두로 포함하지는 않는다. 특히 `goods_receipt_items.purchase_order_item_id`, `purchase_orders.marketplace_id`, `sms_send_logs.template_id` 등은 조회 패턴 확정 후 인덱스 필요성을 검토한다. 작성 시 실행한 카탈로그 비교는 partial index·복합 인덱스의 선택도를 평가하지 않으므로 이 목록을 확정된 성능 결함으로 단정하지 않는다. 데이터량/쿼리 계획 측정 전 DB 변경 금지.

## P2 — 확장 기능·새 데이터 설계

- 매장별 Excel 컬럼 매핑은 DB 저장 테이블이 없다. `marketplaces`는 마켓 마스터만 표현한다.
- 필터교체 안내 대상 제품/사용일수/SMS 사용은 `products`에 해당 필드가 없고 전용 테이블도 없다. `sms_templates`, `sms_send_logs`, `sms_opt_outs`만으로 자동 발송 규칙을 완성할 수 없다.
- BMDMALL 전용 연동 설정·비밀값 저장, 대여제품관리, 지출결의서 테이블이 없다. `/settings/general`은 메뉴에 있으나 `App.jsx` 라우트 목록에서 빠져 404다.
- `system_settings`는 범용 키/값 구조가 있지만 화면 설정의 구체적인 키, 타입, 기본값, 비밀 처리 규칙이 데이터베이스 메타데이터에서 확인되지 않는다. 새 컬럼을 가정하거나 기존 키를 임의 생성하지 않는다.
- SMS 실발송, 배치 실행기, 외부 택배/마켓 연동, Excel 다운로드/업로드의 보관·검증·재시도 규칙은 미정이다. 현 프론트의 Mock 성공 메시지는 실제 처리가 아니다.

## 4-2 권장 범위

1. **첫 묶음 (P0)**: 쓰기 계정과 세션 분리 설계, `users` 인증/로그인 로그, 서버 권한·매장 범위, 표준 오류/감사 로깅. 고정 Mock 사용자를 제거하기 전 로그인 방식·암호 해시 호환성을 확인한다.
2. **둘째 묶음 (P1)**: `stores`·`employees`·`products`·`marketplaces`·공통코드 조회/관리, 고객·상담·A/S의 최소 흐름. `/settings/general` 라우트를 복구한다. 화면 필드와 DB 컬럼 차이를 수정한다.
3. **셋째 묶음 (P1)**: 판매/결제→발주/입고→재고 원장/잔량→물류의 트랜잭션과 상태 이력. 동시 요청·중복 요청·취소를 검증한 뒤 각 화면을 연결한다.
4. **후속 (P2)**: SMS/배치/통계/파일, 시리얼 대량 수정, 저장 구조가 없는 설정·숨김 메뉴는 업무 규칙과 스키마 설계 승인 후 구현한다. 초기 4-2 범위에 115개를 일괄 구현 대상으로 잡지 않는다.

## 보호·검증 기록

- 조회는 `127.0.0.1:5432/new_scm_dev`에 `new_scm_ro`로 접속하여 `transaction_read_only=on` 확인 후 PostgreSQL 시스템 카탈로그와 `alembic_version`에 `SELECT`만 수행했다. 비밀번호/DB URL은 문서·출력에 기록하지 않았다. `asset_manager_dev`에는 접속하지 않았다.
- 문서만 `new-scm/docs/`에 작성했다. 기존 자산관리 `backend`, `frontend`, `.env`, 배포 파일과 신규 SCM 애플리케이션 코드는 수정하지 않았다. 기존 NAS·운영 서비스의 중지/재시작, 배포, 보호 포트 `80`, `8080`, `3010`, `8010` 사용은 없었다.
- 실제 데이터 행의 상태 분포·비밀번호 알고리즘·권한 부여 상태·쿼리 성능은 조회하지 않았으므로 미검증이다. 이 문서의 API 수·매핑 수는 설계 인벤토리이며 기능 구현 수가 아니다.
