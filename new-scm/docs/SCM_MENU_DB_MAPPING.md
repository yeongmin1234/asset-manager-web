# 신규 SCM 화면·DB 매핑 (4-1단계)

2026-10-27 기준. 경로는 브라우저 해시의 `#` 뒤 값이다. 메뉴/라우트 근거는 `frontend/src/App.jsx`, `CustomerConsulting.jsx`, `SettingsManagement.jsx`, `SettingsExtended.jsx`, `pages/WorkspacePages.jsx`; DB 근거는 읽기 전용 실측 [SCM_DB_CATALOG.md](SCM_DB_CATALOG.md)다. 백엔드 업무 API는 **0개**다(`backend/app/main.py`). `frontend/src/services/systemService.js`의 상태 확인 호출만 실제 요청이며 DB 업무 데이터는 아니다.

39개 표시 메뉴 경로의 기계 판독용 표는 [SCM_MENU_DB_MAPPING.csv](SCM_MENU_DB_MAPPING.csv)에 있다. 숨김·메뉴 밖 경로는 아래 별도 표에 기록했다.

## 집계와 판정

- 상단 메뉴 15개: 표시 12개, 숨김 3개. 하위 메뉴 28개: 매장 5, 고객상담 9, 설정 14.
- 표시 메뉴의 고유 경로 39개(상단 경로와 하위 경로의 중복 제거). 이 중 `/settings/general`은 `App.jsx`의 `settingsPaths`에 없어 404로 끝난다. 실제 화면/안내 화면은 38개다.
- 메뉴 밖에 `/activity` 화면 1개가 있다. 숨김 `/rentals`, `/statistics`, `/expenses` 및 숨김 별칭 `/expense-resolution`은 HOME으로 리다이렉트된다. 이 5개는 39개 집계 밖이다.
- 아래 매핑의 **확정**은 프론트 필드와 DB 컬럼·FK의 대응을 뜻한다. 실제 API 연결 완료를 뜻하지 않는다. **유력**은 여러 근거가 있으나 규칙/연결 미검증, **추정**은 업무 의미 중심, **미확인**은 DB 표현 자체가 불분명하다.
- 표시 경로 39개 중 확정 24, 유력 8, 추정 6, 미확인 1(404). 업무 API 연결이 필요한 실제 화면은 38개 모두이며 현재 연결 완료 0개다. 아래 행별 신뢰도와 집계는 설계 판단이며 기능 완료 판정이 아니다.

표의 `id`는 각 테이블의 PK, `A.x→B.id`는 실측 FK다. `R/C/U/D`는 예상 조회/등록/수정/삭제(또는 취소)이고 구현 완료를 의미하지 않는다. 모든 화면은 별도 표기가 없는 한 프론트 메모리/Mock 또는 빈 배열이다. 실제 요청은 설정 화면의 `settingsApiConfigured=false`로 차단된다.

| 메뉴/화면 | URL | 컴포넌트·핸들러/필요 필드 | 관련 테이블·PK/FK | 필요 API·예상 작업 | 데이터 출처/연결 | 신뢰도·누락 |
|---|---|---|---|---|---|---|
| HOME | `/` | `HomeBusinessDashboard`; 요약·최근 주문·알림 이동 | `sales.id`, `purchase_orders.id`, `notices.id`, `inventory_balances.id` | `GET /dashboard/summary` R | 로컬 요약·빈 배열; 미연결 | 유력; 지표 정의·집계 권한 필요 |
| 직원리스트 | `/store-management/staff` | `StaffManagement`; 검색, 등록·수정·퇴사 모달; 직원코드·매장·상태 | `employees.id`, `employees.store_id→stores.id`, `employees.user_id→users.id` | `/employees` R/C/U, 상태 변경 | Mock/로컬; 미연결 | 확정; 퇴사 이력·승인 규칙 필요 |
| 상품등록 | `/store-management/products` | `ProductManagement`; 검색·등록·수정·파일 입력; 상품코드·가격·시리얼 관리 | `products.id`, `product_code`; `marketplaces.id`는 선택 데이터 | `/products` R/C/U, 파일 검증 | 로컬; 미연결 | 확정; 업로드 형식·중복 정책 필요 |
| 매장리스트 | `/store-management/stores` | `StoreSubContent`; 코드·지역·담당자·연락처·상태 | `stores.id`, `code`, `name`, `phone`, `status` | `/stores` R/C/U | 빈 배열; 미연결 | 유력; 화면의 `지역`은 전용 컬럼 없음(주소에서 파생 여부 확인) |
| 매장 통계 | `/store-management/statistics` | `StoreSalesStatistics`; 기간·매장·금액·수량 필터 | `sales.id`, `sales.store_id→stores.id`, `sale_items.sale_id→sales.id` | `/reports/store-sales` R | 로컬 계산; 미연결 | 유력; 취소·환불·공급가 기준 확인 |
| 매장 공지 | `/store-management/notices` | `StoreSubContent`; 등록일·작성자·읽음 | `notices.id`, `notices.target_store_id→stores.id`, `notice_reads.notice_id→notices.id` | `/notices?store_id=` R | 빈 배열; 미연결 | 확정; 공개 범위 필터 필요 |
| 고객상담 기본 | `/customer-consulting` | `AsReception`; 고객/전화/시리얼 검색, 상담등록, 이력 | `customers.id`, `consultations.customer_id→customers.id`, `sales.customer_id`, `as_requests.customer_id`, `logistics_orders.customer_id` | `/customers`, `/consultations`, 고객 이력 R/C | 빈 배열/로컬; 미연결 | 확정; 개인정보 검색·마스킹 필요 |
| A/S 접수 | `/customer-consulting/as-reception` | `AsReception` 및 `AsCreateModal`; 고객·제품·증상·시리얼 | `as_requests.id`, `customer_id→customers.id`, `product_id→products.id`, `source_consultation_id→consultations.id` | `/as-requests` C/R | Mock/모달; 미연결 | 확정; 상담→A/S 중복 전환 검증 |
| 판매 접수 | `/customer-consulting/sales-reception` | `SaleList` 및 판매 모달; 고객·상품·수량·금액 | `sales.id`, `sale_items.sale_id→sales.id`, `sale_payments.sale_id→sales.id` | `/sales` C/R, 결제 | Mock/모달; 미연결 | 확정; 합계·결제 규칙 필요 |
| 상담목록 탭 | `/customer-consulting/consultation-list` | `ConsultationList`; 검색·상세·상태 | `consultations.id`, `consultation_notes.consultation_id→consultations.id` | `/consultations` R/U | Mock/로컬; 미연결 | 확정; 중복 경로와 데이터 일원화 |
| 반품목록 | `/customer-consulting/return-list` | `ReturnList`; 목록/검색 | `goods_receipts.receipt_type=return`, `sales.id` 후보 | `/returns` R/C 설계 보류 | 로컬; 미연결 | 추정; 전용 반품 테이블·판매 환불 관계 없음 |
| 교환목록 | `/customer-consulting/exchange-list` | `ExchangeList`; 목록/검색 | `logistics_orders.logistics_type=exchange` 후보 | `/exchanges` R/C 설계 보류 | 로컬; 미연결 | 추정; 교환 원판매·대체품 관계 불명 |
| A/S 목록 탭 | `/customer-consulting/as-list` | `AsList`; 검색·상세 | `as_requests.id`, `as_status_histories.as_request_id→as_requests.id` | `/as-requests` R/U | Mock; 미연결 | 확정; 상단 A/S와 데이터 일원화 |
| 판매목록 탭 | `/customer-consulting/sales-list` | `SaleList`; 검색·상세 | `sales.id`, `sale_items.sale_id→sales.id` | `/sales` R | Mock; 미연결 | 확정; 상단 판매와 데이터 일원화 |
| 입출고목록 | `/customer-consulting/logistics-list` | `InOutList`; 검색·필터·상세 | `goods_receipts.id`, `logistics_orders.id`, `inventory_movements.id` | `/goods-receipts`, `/logistics-orders`, `/inventory-movements` R | 로컬; 미연결 | 유력; 목록의 입·출고 정의 확인 |
| 입출고관리 | `/customer-consulting/logistics-management` | `InOutManagement`; 등록·상태·시리얼 | `logistics_orders.id`, `logistics_items.logistics_order_id→logistics_orders.id`, `inventory_movements.id` | `/logistics-orders` C/U, 출고 처리 | 로컬; 미연결 | 유력; 물류/재고 트랜잭션 경계 필요 |
| 고객관리 | `/customers` | `CustomerManagementPage`; 검색·초기화만, 고객명/연락처 | `customers.id`, `customer_code`, `name`, `phone_normalized` | `/customers` R/C/U | 빈 상태; 미연결 | 확정; 등록·상세·수정 UI 없음 |
| 상담목록 | `/consultations` | `ConsultationList`; 검색·등록·상세·메모 | `consultations.id`, `consultation_notes.consultation_id→consultations.id` | `/consultations` R/C/U, `/notes` | Mock; 미연결 | 확정; 상태/메모 저장 없음 |
| A/S | `/as` | `AsManagement`; 검색·접수·상태·메모 | `as_requests.id`, `as_notes.as_request_id→as_requests.id`, `as_status_histories.as_request_id→as_requests.id` | `/as-requests` R/C/U, 상태/메모 | Mock; 미연결 | 확정; 시리얼·보증 검증 필요 |
| 판매 | `/sales` | `SalesManagement`; 검색·등록·결제·상태 | `sales.id`, `sale_items.sale_id`, `sale_payments.sale_id`, `sale_status_histories.sale_id` | `/sales` R/C/U, `/payments` | Mock; 미연결 | 확정; 금액·재고·환불 원자성 필요 |
| 물류 | `/logistics` | `LogisticsManagement`; 검색·등록·송장·상태 | `logistics_orders.id`, `logistics_items.logistics_order_id`, `shipments.logistics_order_id`, `logistics_status_histories.logistics_order_id` | `/logistics-orders` R/C/U, `/shipments` | Mock; 미연결 | 확정; 판매/A/S 원천 연결 검증 |
| 발주지원센터 | `/order-support` | `OrderSupportPage`; 검색만, 요청번호/상품 | `purchase_orders.id`, `purchase_order_items.purchase_order_id→purchase_orders.id` | `/purchase-orders` R/C/U | 빈 상태; 미연결 | 확정; 발주·입고 UI 없음 |
| 공지사항 | `/notices` | `NoticeManagement`; 검색·작성·게시·읽음 | `notices.id`, `notice_reads.notice_id→notices.id`, `notice_reads.user_id→users.id` | `/notices` R/C/U, 읽음 | Mock; 미연결 | 확정; 공개 범위·게시기간 검사 |
| 메모검색 | `/memo-search` | `MemoSearchPage`; 내용 검색만 | `memos.id`, `entity_type`, `entity_id` (다형 관계, FK 아님) | `/memos` R | 빈 상태; 미연결 | 유력; 대상별 접근권한·삭제 필터 필요 |
| 환경설정 첫 화면 | `/settings` | `SettingsManagement`; 좌측 안내 | `system_settings.id`는 하위 기본설정 후보 | `/system-settings` R | 안내만; 미연결 | 추정; 첫 화면을 실제 설정 목록으로 할지 확인 |
| 공통/기본 설정 | `/settings/general` | 메뉴 버튼은 존재, `App.jsx` 경로 집합 밖 | `system_settings.id`, `setting_key` 후보 | `/system-settings` R/U | **404** | 미확인; 라우트 추가와 `SettingsStage12` 연결 필요 |
| 계정관리 | `/settings/accounts` | `AccountManagement`; 검색·등록·상태 | `users.id`, `username`, `password_hash`, `account_type`, `status`; `employees.user_id→users.id` | `/users` R/C/U | Mock/로컬; 미연결 | 확정; 서버 인증/권한·비밀번호 정책 필요 |
| 코드관리 | `/settings/codes` | `SettingsStage12`; 그룹/코드 조회 | `common_code_groups.id`, `common_codes.group_id→common_code_groups.id` | `/code-groups`, `/codes` R/C/U | 서비스 stub; 미연결 | 확정; 코드 사용 중 변경 규칙 필요 |
| 배치관리 | `/settings/batches` | `SettingsStage12`; 목록·수동 실행 | `batch_jobs.id`, `batch_job_runs.batch_job_id→batch_jobs.id` | `/batch-jobs` R, `/runs` R/C | 서비스 stub; 미연결 | 확정; 실행기·동시 실행 제어 없음 |
| 마켓 | `/settings/markets` | `SettingsManagement`; 검색·등록 | `marketplaces.id`, `code`, `name`, `status` | `/marketplaces` R/C/U | Mock/로컬; 미연결 | 확정; 매출 사용 중 비활성 정책 필요 |
| 데이터 매핑 | `/settings/data-mapping` | `SettingsManagement`; 마켓별 Excel 컬럼 규칙 등록 | `marketplaces.id`만 존재; 규칙 저장 테이블 없음 | `/marketplace-mappings` 설계 보류 | Mock/로컬; 미연결 | 추정; 신규 테이블/파일 양식 규칙 필요 |
| A/S 설정 | `/settings/as` | `AsSettings`; 기본 상태·담당자·기간 저장 | `system_settings.id` 후보; `as_requests.status` 참고 | `/system-settings` R/U | 로컬 폼; 미연결 | 유력; 설정 키·값 스키마와 기본값 정의 필요 |
| 증상/파트관리 | `/settings/symptoms` | `SettingsStage12`; 증상·부품 목록 | `as_symptom_codes.id`, `as_part_codes.id`, `as_part_codes.product_id→products.id` | `/as-symptoms`, `/as-parts` R/C/U | 서비스 stub; 미연결 | 확정; 구형 `SymptomManagement`은 렌더되지 않음 |
| 필터교체 SMS | `/settings/filter-sms` | `SettingsStage12`; 템플릿 목록 | `sms_templates.id`, `system_settings.id` 후보 | `/sms-templates` R/C/U, dry-run | 서비스 stub; 미연결 | 유력; 대상제품·발송 규칙 전용 테이블 없음 |
| 발송현황 | `/settings/send-status` | `SettingsStage12`; 이력 목록 | `sms_send_logs.id`, `customer_id→customers.id`, `template_id→sms_templates.id` | `/sms-send-logs` R | 서비스 stub; 미연결 | 확정; 발송/예약은 별도 정책 필요 |
| 수신거부 지정 | `/settings/opt-out` | `SettingsStage12`; 거부 목록 | `sms_opt_outs.id`, `customer_id→customers.id` | `/sms-opt-outs` R/C/U | 서비스 stub; 미연결 | 확정; 전화번호 해시·동의 충돌 처리 필요 |
| 대상 제품관리 | `/settings/target-products` | `Products`; 등록·목록, 사용일수/SMS 사용 | `products.id`는 제품 마스터; 전용 대상·주기 컬럼 없음 | `/sms-target-products` 설계 보류 | Mock/로컬; 미연결 | 추정; 신규 테이블 또는 규칙 구조 필요 |
| BMDMALL | `/settings/bmdmall` | `BmdMall`; 사용·기본 마켓·제품 매핑 | `marketplaces.id`, `system_settings.id` 후보 | `/integrations/bmdmall` 설계 보류 | 로컬 폼; 미연결 | 추정; 외부 연동 설정/자격정보 구조 없음 |
| 시리얼번호 업데이트 | `/settings/serial-update` | `SettingsStage12`; XLSX 업로드→검증→승인→적용 | `serial_bulk_update_jobs.id`, `serial_bulk_update_items.job_id→serial_bulk_update_jobs.id`, `serial_number_corrections.bulk_update_job_id`, `serial_inventories.id` | `/serial-bulk-jobs` R/C, 단계 전이 | 서비스 stub; 미연결 | 확정; 파일 저장·승인 분리·중복 검사 필요 |

## 메뉴 밖·숨김 경로

| 경로 | 현재 동작 | DB 대응·결정 |
|---|---|---|
| `/activity` | `ActivityHistory` 렌더, 상단 메뉴 없음; `activityBridge` 로컬 기록 | `audit_logs.id` 유력. 서버 감사 로그와 화면 기록의 범위가 다를 수 있어 권한/보존 정책 확인 필요 |
| `/rentals` | 숨김, HOME 리다이렉트 | 대여 테이블 없음. 신규 업무 모델·범위 결정 전 API 설계 보류 |
| `/statistics` | 숨김, HOME 리다이렉트 | `sales` 등 집계 후보. 표시 통계와 범위 결정 필요 |
| `/expenses`, `/expense-resolution` | 숨김, HOME 리다이렉트 | 지출결의 전용 테이블 없음. 신규 설계 필요 |

## 공통 미구현 사항

- 검색/필터/모달/등록·수정·삭제 버튼은 다수 존재하지만 대부분 로컬 `useState`만 변경한다. 새로고침 후 영속성이 없고 서버 검증·감사 로그가 없다.
- 파일 선택/검증 컴포넌트는 있지만 실제 업로드·다운로드 저장 경로와 서버 스캔·권한 정책이 없다. `SettingsStage12`의 파일 API는 stub이고 `SettingsExtended`의 구형 시리얼 업로드는 mock 타이머다.
- `frontend/src/contexts/AuthContext.jsx`는 `CURRENT_USER_MOCK` 고정 사용자, `services/authService.js`는 로그인 stub이다. 메뉴 숨김은 서버 권한 검사가 아니다.
- `SettingsManagement.jsx`의 계정·코드·배치 패널은 각각 `AccountManagement`/`SettingsStage12`로 대체 렌더된다. 같은 파일 안의 seed/추가 코드가 실제 화면 동작으로 이어지지 않는 부분을 구현 완료로 세지 않았다.
- 우선순위: P0 인증·권한·개인정보·원자적 상태변경, P1 기준정보/고객/상담/A/S/판매/발주·재고·물류, P2 통계/Excel/SMS/배치·보조 설정.
