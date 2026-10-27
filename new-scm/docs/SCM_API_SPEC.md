# 신규 SCM FastAPI 상세 API 설계 (미구현)

2026-10-27 기준. 근거: `backend/app/main.py`, `backend/app/db/database.py`, `frontend/src/services/*.js`, [실측 DB 카탈로그](SCM_DB_CATALOG.md), [화면 매핑](SCM_MENU_DB_MAPPING.md). **아래 업무 API는 모두 설계안이며 구현·연결 0건**이다. 현재 백엔드의 `GET /api/v1/system/status`, 진단 키가 필요한 `GET /api/v1/system/db-status`, `GET /health`만 동작한다. 진단 API는 업무 API 개수에서 제외한다.

설계안은 **115개**(GET 48, POST 47, PATCH 18, DELETE 2)이며 인증 공개 경로는 로그인 1개뿐이다. HTTP method 기준 읽기 48/쓰기 67개다. `POST /sms/dry-run`은 쓰기 method이지만 DB와 외부 SMS에는 쓰지 않는다. 영역별 개수는 [간극 분석](SCM_GAP_ANALYSIS.md)에 정리했다.

## 공통 계약

- 경로 접두사 `/api/v1`. FastAPI 라우터→서비스→SQLAlchemy 세션→PostgreSQL. `GET`은 읽기 트랜잭션, 쓰기는 요청 단위 트랜잭션으로 완료/롤백한다. `backend/app/db/database.py`의 **현재 DB 엔진은 읽기 전용 진단 전용**이므로 업무 쓰기 세션·계정 설계와 분리해야 한다.
- 응답 `{"ok":true,"data":...,"error":null}` / 실패 `{"ok":false,"data":null,"error":{"code":"...","message":"..."}}`. 목록 `data={"items":[],"total":0,"page":1,"page_size":20}`; 상세는 실제 테이블 필드만 반환. 민감 필드 `users.password_hash`, 전화번호 해시, 내부 로그 페이로드는 반환 금지. 현재 예외 처리 형식과 맞춘다.
- 목록 기본 `page=1,page_size=20`(최대 100), `sort`는 명시한 컬럼 allowlist만, 검색은 서버 측 권한 범위/`is_deleted=false` 우선. 날짜는 ISO 8601, 금액은 decimal 문자열, 시각은 timezone 포함. `id`는 DB PK 정수. 필터값은 서버 스키마에서 검증한다.
- 인증: 아래 `조회`, `담당`, `관리`, `승인`, `감사`는 **제안된 권한 범주**다. 현재 `users.account_type`과 `status`는 존재하지만 역할별 상세 권한 테이블은 없다. 실제 매장별 접근 범위, 관리자 범위, 승인자 분리 정책은 확인 필요다. 모든 업무 API는 서버에서 활성 사용자/권한/매장 범위를 검사한다. 공개 경로는 로그인만.
- 기본 오류: 인증 401, 권한 403, 대상 없음 404, 중복·상태 충돌 409, 형식/범위 422, 예상치 못한 오류 500. 쓰기 요청에 재시도 키(`Idempotency-Key`)를 적용할 대상은 결제/재고/시리얼/발송 등이며 보관 방식은 4-2 확정 필요다. 409는 실제 unique index나 상태 잠금 충돌을 함께 다룬다.
- `POST`는 생성된 리소스 상세, `PATCH`는 수정된 상세, 상태 전이는 변경된 상세와 기록 ID, `GET` 상세는 관련 이력/항목 포함 여부를 명시한 스키마를 사용한다. `DELETE`는 실제 `is_deleted` 컬럼이 있는 리소스에서만 soft delete를 기본으로 제안한다. 다른 테이블에는 물리 삭제 API를 우선 설계하지 않는다.
- 표에서 `Q`는 `page,page_size,q,sort`와 명시 필터, `D`는 해당 테이블의 공개 가능한 실제 컬럼, `S`는 상태 전이 요청 `{new_status,reason}`을 뜻한다. `R`은 읽기 전용, `W`는 쓰기 트랜잭션, `W*`는 다중 테이블 원자 작업. 각 행의 `V`는 추가 검증, `E`는 기본 오류 외 예상 코드다. `T`에 테이블을 정확히 표시했다.

## 인증·사용자·기준정보 (P0/P1)

| Method·Endpoint | 기능; 요청 → 응답 | T | V; 권한; E; 트랜잭션 |
|---|---|---|---|
| `POST /auth/login` | `username,password` → 사용자 공개 필드·서버 세션 | `users`, `login_logs` | `status` 활성·비밀번호 해시 검증; 공개; `invalid_credentials`, `inactive_user`; W* |
| `POST /auth/logout` | 세션 식별 → 종료 확인 | 세션 저장소 미정, `audit_logs` | 현재 세션만; 로그인; `session_not_found`; W |
| `GET /auth/me` | 없음 → `users.id,username,name,account_type,status`·권한 범위 | `users` | 활성 세션; 로그인; `session_expired`; R |
| `GET /users` | Q+`status,account_type` → 목록 | `users` | `password_hash` 제외; 관리; 기본; R |
| `GET /users/{id}` | 없음 → 공개 D | `users` | 매장/본인 범위 확인; 관리 또는 본인; 기본; R |
| `POST /users` | `username,name,password,account_type,status` → 공개 D | `users`,`audit_logs` | username 유일·해시 생성·허용 account_type; 관리; `duplicate_username`; W* |
| `PATCH /users/{id}` | `name,email,status,account_type` → 공개 D | `users`,`audit_logs` | 자기 권한 상승 금지·최종 관리자 규칙 확인; 관리; `last_admin_conflict`; W* |
| `POST /users/{id}/password-reset` | 임시 인증/새 비밀번호 정책값 → 결과 | `users`,`audit_logs` | 기존/관리 인증·해시 교체·세션 무효화 정책; 관리/본인; `weak_password`; W* |
| `GET /stores` | Q+`status` → 목록 | `stores` | 허용 매장 범위; 조회; 기본; R |
| `GET /stores/{id}` | 없음 → D | `stores` | 허용 매장 범위; 조회; 기본; R |
| `POST /stores` | `code,name,status` 및 선택 `phone,address,manager_name` → D | `stores`,`audit_logs` | code 유일·status CHECK; 관리; `duplicate_code`; W* |
| `PATCH /stores/{id}` | 수정 가능 실제 컬럼 → D | `stores`,`audit_logs` | 참조/폐점 정책 확인; 관리; `referenced_store`; W* |
| `GET /employees` | Q+`store_id,employment_status,approval_status` → 목록 | `employees`,`stores` | 매장 범위; 조회; 기본; R |
| `GET /employees/{id}` | 없음 → D | `employees` | 매장 범위; 조회; 기본; R |
| `POST /employees` | `employee_code,store_id,name,position,joined_at` 등 → D | `employees`,`stores`,`audit_logs` | store 존재·employee_code 유일·user_id 1:1; 관리; `duplicate_code`; W* |
| `PATCH /employees/{id}` | `position,phone,email,memo,store_id` 등 → D | `employees`,`audit_logs` | 소속 이동/재직 상태 규칙; 관리; `invalid_transition`; W* |
| `POST /employees/{id}/resignation` | `resigned_at,resignation_reason` → D | `employees`,`audit_logs` | 재직자만·승인 미결건 처리; 관리; `invalid_transition`; W* |
| `GET /marketplaces` | Q+`status` → 목록 | `marketplaces` | 정렬 allowlist; 조회; 기본; R |
| `POST /marketplaces` | `code,name,marketplace_type,status` → D | `marketplaces`,`audit_logs` | code 유일·status CHECK; 관리; `duplicate_code`; W* |
| `PATCH /marketplaces/{id}` | 실제 수정 가능 컬럼 → D | `marketplaces`,`audit_logs` | 판매/발주 참조 시 비활성 정책; 관리; `in_use`; W* |
| `GET /code-groups` | Q+`is_active` → 그룹·코드 수 | `common_code_groups`,`common_codes` | 비활성 필터; 조회; 기본; R |
| `POST /code-groups` | `group_code,group_name,description` → D | `common_code_groups`,`audit_logs` | group_code 유일; 관리; `duplicate_code`; W* |
| `PATCH /code-groups/{id}` | `group_name,description,is_active,sort_order` → D | `common_code_groups`,`audit_logs` | 시스템 그룹 보호; 관리; `system_group_locked`; W* |
| `GET /code-groups/{id}/codes` | Q → 목록 | `common_codes` | group 존재; 조회; 기본; R |
| `POST /code-groups/{id}/codes` | `code,name,extra_value,is_default` → D | `common_codes`,`audit_logs` | `(group_id,code)` 유일·기본값 하나 정책; 관리; `duplicate_code`; W* |
| `PATCH /codes/{id}` | `name,description,is_active,sort_order` → D | `common_codes`,`audit_logs` | 참조 중 코드 변경 제한; 관리; `in_use`; W* |
| `GET /system-settings` | Q+`category` → 비밀값 제외 목록 | `system_settings` | `is_secret` 마스킹; 관리; 기본; R |
| `PATCH /system-settings/{id}` | `setting_value` → 비밀값 제외 D | `system_settings`,`audit_logs` | `is_editable`, `value_type`, `validation_rule`; 관리; `not_editable`; W* |

## 고객·상담·A/S (P1)

| Method·Endpoint | 기능; 요청 → 응답 | T | V; 권한; E; 트랜잭션 |
|---|---|---|---|
| `GET /customers` | Q+`name,phone_normalized,status,is_vip` → 마스킹 목록 | `customers` | 연락처 정확검색/마스킹·삭제 제외; 조회; 기본; R |
| `GET /customers/{id}` | 없음 → 공개 D·요약 | `customers` | 개인정보 열 권한; 담당; 기본; R |
| `POST /customers` | `customer_code,name` 및 연락처·동의 → D | `customers`,`audit_logs` | code 유일·동의 기록 정책·전화 정규화; 담당; `duplicate_code`; W* |
| `PATCH /customers/{id}` | 실제 수정 가능 컬럼 → D | `customers`,`audit_logs` | 동의 변경 기록·낙관 잠금 필요; 담당; `stale_record`; W* |
| `DELETE /customers/{id}` | 삭제 사유 → 삭제 상태 | `customers`,`audit_logs` | 참조 판매/상담 처리 정책 확정 전 보류; 관리; `referenced_customer`; W* |
| `GET /customers/{id}/history` | Q+유형 → 상담/A/S/판매/물류 요약 | `consultations`,`as_requests`,`sales`,`logistics_orders` | 고객 FK로만 결합·권한; 담당; 기본; R |
| `GET /consultations` | Q+`customer_id,status,assigned_employee_id` → 목록 | `consultations` | 매장 범위는 고객/담당 기준 협의; 조회; 기본; R |
| `GET /consultations/{id}` | 없음 → D·notes | `consultations`,`consultation_notes` | 내부 메모 열 권한; 담당; 기본; R |
| `POST /consultations` | `customer_id,consultation_type,channel,title,content,priority` → D | `consultations`,`audit_logs` | 고객 존재·code 생성·상태 CHECK; 담당; `invalid_customer`; W* |
| `PATCH /consultations/{id}` | `title,content,assigned_employee_id,priority` → D | `consultations`,`audit_logs` | 완료/취소 후 편집 정책; 담당; `invalid_transition`; W* |
| `POST /consultations/{id}/status` | S → D·history | `consultations`,`audit_logs` | 허용 전이표 확정 필요; 담당; `invalid_transition`; W* |
| `POST /consultations/{id}/notes` | `content,is_internal` → note D | `consultation_notes`,`audit_logs` | 내용 비공백·내부 열 권한; 담당; `forbidden_note`; W* |
| `GET /as-requests` | Q+`customer_id,status,serial_number` → 목록 | `as_requests` | 삭제 제외·시리얼 정확검색; 조회; 기본; R |
| `GET /as-requests/{id}` | 없음 → D·notes·status history | `as_requests`,`as_notes`,`as_status_histories` | 고객/매장 범위; 담당; 기본; R |
| `POST /as-requests` | `customer_id,product_id,serial_number,request_type,symptom,warranty_status` 등 → D | `as_requests`,`as_status_histories`,`audit_logs` | 고객·제품 존재, 상담 참조 unique, code unique; 담당; `duplicate_consultation`; W* |
| `PATCH /as-requests/{id}` | `assigned_employee_id,diagnosis,resolution,expected_completion_at` → D | `as_requests`,`audit_logs` | 상태별 수정 가능 필드; 담당; `invalid_transition`; W* |
| `POST /as-requests/{id}/status` | S → D·history | `as_requests`,`as_status_histories`,`audit_logs` | CHECK 값 + 허용 전이 + 시간 필드; 담당; `invalid_transition`; W* |
| `POST /as-requests/{id}/notes` | `note_type,content` → note D | `as_notes`,`audit_logs` | note_type CHECK·내용 비공백; 담당; `invalid_note_type`; W* |
| `GET /as-symptoms` | Q+`category_code,is_active` → 목록 | `as_symptom_codes` | 제품별 직접 FK는 없음; 조회; 기본; R |
| `POST /as-symptoms` | `symptom_code,symptom_name,default_priority,requires_serial` → D | `as_symptom_codes`,`audit_logs` | code unique·우선순위 CHECK; 관리; `duplicate_code`; W* |
| `PATCH /as-symptoms/{id}` | 명칭·활성·정렬 → D | `as_symptom_codes`,`audit_logs` | 사용 중 비활성 정책; 관리; `in_use`; W* |
| `GET /as-parts` | Q+`product_id,is_active` → 목록 | `as_part_codes`,`products` | product FK; 조회; 기본; R |
| `POST /as-parts` | `part_code,part_name,product_id,standard_cost` → D | `as_part_codes`,`audit_logs` | code unique·비용 비음수; 관리; `duplicate_code`; W* |
| `PATCH /as-parts/{id}` | 명칭·비용·활성 → D | `as_part_codes`,`audit_logs` | 제품 참조·비용 CHECK; 관리; `invalid_cost`; W* |

## 상품·판매·발주·재고·물류 (P1)

| Method·Endpoint | 기능; 요청 → 응답 | T | V; 권한; E; 트랜잭션 |
|---|---|---|---|
| `GET /products` | Q+`product_code,barcode,status,serial_managed` → 목록 | `products` | 가격 열 권한; 조회; 기본; R |
| `GET /products/{id}` | 없음 → D | `products` | 비용가 열 권한; 조회; 기본; R |
| `POST /products` | `product_code,name,status,serial_managed,warranty_months` 등 → D | `products`,`audit_logs` | code·barcode unique, 가격/안전재고 비음수; 관리; `duplicate_code`; W* |
| `PATCH /products/{id}` | 실제 수정 가능 컬럼 → D | `products`,`audit_logs` | 판매 후 코드/시리얼 관리 변경 정책; 관리; `in_use`; W* |
| `GET /sales` | Q+`customer_id,store_id,status,sold_at` → 목록 | `sales`,`customers`,`stores` | 매장 범위·삭제 제외; 조회; 기본; R |
| `GET /sales/{id}` | 없음 → D·items·payments·history | `sales`,`sale_items`,`sale_payments`,`sale_status_histories` | 결제정보 마스킹; 담당; 기본; R |
| `POST /sales` | `customer_id,store_id,employee_id,sale_type,sold_at,items[]` → D | `sales`,`sale_items`,`sale_status_histories`,`audit_logs` | FK·수량·단가·합계·code unique; 담당; `amount_mismatch`; W* |
| `PATCH /sales/{id}` | 초안 `items[],discount_amount,memo` → D | `sales`,`sale_items`,`audit_logs` | 초안만·서버 재계산; 담당; `invalid_transition`; W* |
| `POST /sales/{id}/payments` | `payment_method,amount,paid_at,reference_number` → 결제 D·판매 합계 | `sale_payments`,`sales`,`sale_status_histories`,`audit_logs` | 양수·잔액·중복키·잠금; 담당; `overpayment`; W* |
| `POST /sales/{id}/status` | S → D·history | `sales`,`sale_status_histories`,`audit_logs` | 결제/취소/환불 전이 규칙; 담당; `invalid_transition`; W* |
| `GET /purchase-orders` | Q+`store_id,status,expected_receipt_date` → 목록 | `purchase_orders` | 매장 범위; 조회; 기본; R |
| `GET /purchase-orders/{id}` | 없음 → D·items·history | `purchase_orders`,`purchase_order_items`,`purchase_order_status_histories` | 매장 범위; 담당; 기본; R |
| `POST /purchase-orders` | `requesting_store_id,items[{product_id,ordered_quantity,unit_cost}]` → D | `purchase_orders`,`purchase_order_items`,`audit_logs` | FK·수량·금액·code unique; 담당; `invalid_quantity`; W* |
| `PATCH /purchase-orders/{id}` | 초안 항목/일정/메모 → D | `purchase_orders`,`purchase_order_items`,`audit_logs` | 초안만·입고 수량 보호; 담당; `invalid_transition`; W* |
| `POST /purchase-orders/{id}/status` | S → D·history | `purchase_orders`,`purchase_order_status_histories`,`audit_logs` | 승인 분리·입고량에 따른 상태; 승인; `invalid_transition`; W* |
| `GET /goods-receipts` | Q+`purchase_order_id,store_id,status` → 목록 | `goods_receipts` | 매장 범위; 조회; 기본; R |
| `GET /goods-receipts/{id}` | 없음 → D·items | `goods_receipts`,`goods_receipt_items` | 매장 범위; 담당; 기본; R |
| `POST /goods-receipts` | `store_id,receipt_type,purchase_order_id?,items[]` → D | `goods_receipts`,`goods_receipt_items`,`audit_logs` | 입고 수량·상품·발주항목 FK; 담당; `over_receipt`; W* |
| `POST /goods-receipts/{id}/complete` | 확정 요청 → D·잔량 | `goods_receipts`,`goods_receipt_items`,`purchase_order_items`,`inventory_balances`,`inventory_movements`,`serial_inventories`,`audit_logs` | 잠금·중복처리 방지·수량 보존; 담당; `already_completed`; W* |
| `GET /inventory-balances` | Q+`store_id,product_id,below_safety_stock` → 목록 | `inventory_balances`,`products` | 매장 범위; 조회; 기본; R |
| `GET /inventory-movements` | Q+`store_id,product_id,source_type,from,to` → 원장 | `inventory_movements` | 매장 범위·불변 원장; 조회; 기본; R |
| `GET /serial-inventories` | Q+`serial_number,product_id,store_id,status` → 목록 | `serial_inventories` | 시리얼 정확 검색·매장 범위; 조회; 기본; R |
| `GET /stock-transfers` | Q+`origin_store_id,destination_store_id,status` → 목록 | `stock_transfers`,`stock_transfer_items` | 양쪽 매장 범위; 조회; 기본; R |
| `POST /stock-transfers` | `origin_store_id,destination_store_id,items[]` → D | `stock_transfers`,`stock_transfer_items`,`audit_logs` | 출발≠도착·재고/시리얼 유효; 담당; `insufficient_stock`; W* |
| `POST /stock-transfers/{id}/status` | S → D·history·잔량 | `stock_transfers`,`stock_transfer_status_histories`,`inventory_balances`,`inventory_movements`,`serial_inventories`,`audit_logs` | 출발/도착 원자 이동·승인 분리; 승인; `invalid_transition`; W* |
| `GET /inventory-adjustments` | Q+`store_id,status` → 목록 | `inventory_adjustments`,`inventory_adjustment_items` | 매장 범위; 조회; 기본; R |
| `POST /inventory-adjustments` | `store_id,reason,items[{product_id,adjustment_quantity}]` → D | `inventory_adjustments`,`inventory_adjustment_items`,`audit_logs` | 0 아닌 수량·사유; 담당; `invalid_quantity`; W* |
| `POST /inventory-adjustments/{id}/apply` | 승인 후 반영 → D·잔량 | `inventory_adjustments`,`inventory_balances`,`inventory_movements`,`audit_logs` | 승인자 분리·음수 재고 방지; 승인; `insufficient_stock`; W* |
| `GET /logistics-orders` | Q+`source_type,status,customer_id` → 목록 | `logistics_orders` | 매장·고객 범위; 조회; 기본; R |
| `GET /logistics-orders/{id}` | 없음 → D·items·shipments·history | `logistics_orders`,`logistics_items`,`shipments`,`logistics_status_histories` | 개인정보/주소 마스킹; 담당; 기본; R |
| `POST /logistics-orders` | `source_type,source_sale_id?,source_as_request_id?,logistics_type,items[]` → D | `logistics_orders`,`logistics_items`,`audit_logs` | 원천 타입/ID 일치·unique source index; 담당; `duplicate_source`; W* |
| `POST /logistics-orders/{id}/status` | S → D·history·재고 결과 | `logistics_orders`,`logistics_status_histories`,`inventory_balances`,`inventory_movements`,`serial_inventories`,`audit_logs` | 출고 시 재고 반영·중복 방지; 담당; `invalid_transition`; W* |
| `POST /logistics-orders/{id}/shipments` | `carrier_code,carrier_name,tracking_number` → shipment D | `shipments`,`logistics_orders`,`audit_logs` | `(logistics_order_id,tracking_number)` unique; 담당; `duplicate_tracking`; W* |
| `POST /logistics-orders/{id}/notes` | `note_type,content` → note D | `logistics_notes`,`audit_logs` | note_type CHECK·내용 비공백; 담당; 기본; W* |

## 공지·메모·SMS·배치·시리얼·통계 (P1/P2)

| Method·Endpoint | 기능; 요청 → 응답 | T | V; 권한; E; 트랜잭션 |
|---|---|---|---|
| `GET /notices` | Q+`status,visibility_type,store_id` → 목록 | `notices`,`notice_reads` | 게시기간·대상 필터; 조회; 기본; R |
| `GET /notices/{id}` | 없음 → D·읽음 상태 | `notices`,`notice_reads` | 접근 범위·조회수 집계 정책; 조회; 기본; R |
| `POST /notices` | `title,content,visibility_type,target_store_id?,target_role?` → D | `notices`,`audit_logs` | 대상 타입별 필수값·게시기간; 관리; `invalid_target`; W* |
| `PATCH /notices/{id}` | 제목·본문·게시/닫힘 필드 → D | `notices`,`audit_logs` | 게시 후 변경 정책; 관리; `invalid_transition`; W* |
| `POST /notices/{id}/read` | 없음 → `first_read_at,last_read_at,read_count` | `notice_reads` | `(notice_id,user_id)` unique upsert; 로그인; 기본; W |
| `GET /memos` | Q+`entity_type,entity_id,target_store_id` → 목록 | `memos` | 다형 대상 권한·삭제 제외; 조회; 기본; R |
| `POST /memos` | `content,memo_type,entity_type,entity_id?,target_store_id?` → D | `memos`,`audit_logs` | 대상 실재 검사(실제 FK 없음); 담당; `invalid_target`; W* |
| `PATCH /memos/{id}` | `title,content,is_pinned` → D | `memos`,`audit_logs` | 작성자/관리자만; 담당; `not_owner`; W* |
| `DELETE /memos/{id}` | 없음 → 삭제 상태 | `memos`,`audit_logs` | soft delete; 작성자/관리자; `not_owner`; W* |
| `GET /sms-templates` | Q+`category,is_active` → 목록 | `sms_templates` | 변수 허용목록; 관리; 기본; R |
| `POST /sms-templates` | `template_code,template_name,message_type,category,content,allowed_variables` → D | `sms_templates`,`audit_logs` | code unique·템플릿 변수 검증; 관리; `invalid_variable`; W* |
| `PATCH /sms-templates/{id}` | 내용·활성 → D | `sms_templates`,`audit_logs` | 발송 이력 보존; 관리; `in_use`; W* |
| `GET /sms-send-logs` | Q+`status,category,from,to` → 마스킹 이력 | `sms_send_logs` | 전화번호 원문 미저장·범위; 관리; 기본; R |
| `POST /sms/dry-run` | `template_id,customer_id` → 렌더 미리보기·발송 가능 여부 | `sms_templates`,`customers`,`sms_opt_outs` | 동의·거부·변수 검사, 외부 발송 없음; 관리; `opted_out`; R |
| `GET /sms-opt-outs` | Q+`is_active,phone_last4` → 마스킹 목록 | `sms_opt_outs` | 해시 검색 방식 확인; 관리; 기본; R |
| `POST /sms-opt-outs` | `customer_id?,phone` 및 `opt_out_type,reason` → D | `sms_opt_outs`,`audit_logs` | 전화 정규화·해시·중복 활성 거부; 관리; `duplicate_opt_out`; W* |
| `POST /sms-opt-outs/{id}/revoke` | 사유 → D | `sms_opt_outs`,`audit_logs` | 현재 활성만·동의와 별개; 관리; `already_revoked`; W* |
| `GET /batch-jobs` | Q+`is_enabled,job_type` → 목록 | `batch_jobs` | 작업 정의 권한; 관리; 기본; R |
| `GET /batch-jobs/{id}/runs` | Q → 실행 이력 | `batch_job_runs` | 오류 메시지 비밀값 제거; 관리; 기본; R |
| `POST /batch-jobs/{id}/runs` | 수동 실행 사유 → run D | `batch_jobs`,`batch_job_runs`,`audit_logs` | enabled·중복 실행 잠금·실행기 필요; 관리; `already_running`; W* |
| `GET /serial-bulk-jobs` | Q+`status` → 목록 | `serial_bulk_update_jobs` | 개인정보/원본 파일 접근 범위; 관리; 기본; R |
| `GET /serial-bulk-jobs/{id}` | 없음 → job D·검증 요약/항목 페이지 | `serial_bulk_update_jobs`,`serial_bulk_update_items`,`serial_number_corrections` | 항목 대량 페이징; 관리; 기본; R |
| `POST /serial-bulk-jobs` | multipart XLSX + `reason` → draft job D | `serial_bulk_update_jobs`,`serial_bulk_update_items`,`audit_logs` | 확장자·크기·행수·중복·파일 검사; 관리; `invalid_file`; W* |
| `POST /serial-bulk-jobs/{id}/validate` | 없음 → 검증 결과 | `serial_bulk_update_jobs`,`serial_bulk_update_items`,`serial_inventories`,`audit_logs` | 원본/대상 시리얼 유일·존재; 관리; `validation_failed`; W* |
| `POST /serial-bulk-jobs/{id}/approve` | 승인 사유 → approved D | `serial_bulk_update_jobs`,`audit_logs` | 요청자≠승인자 정책; 승인; `self_approval`; W* |
| `POST /serial-bulk-jobs/{id}/apply` | 재확인 키 → applied D·corrections | `serial_bulk_update_jobs`,`serial_bulk_update_items`,`serial_inventories`,`serial_number_corrections`,`audit_logs` | 재검증·잠금·중복 처리 방지; 승인; `serial_conflict`; W* |
| `GET /dashboard/summary` | `store_id?,from,to` → 매출·상담·A/S·재고 요약 | `sales`,`consultations`,`as_requests`,`inventory_balances` | 지표 정의·권한 범위; 조회; 기본; R |
| `GET /reports/store-sales` | `from,to,store_ids[],basis` → 매장별 합계 | `sales`,`sale_items`,`stores` | 취소 제외·공급가 근거 미정; 조회; `unsupported_basis`; R |
| `GET /audit-logs` | Q+`actor_user_id,entity_type,from,to` → 마스킹 이력 | `audit_logs` | before/after 민감값 제거; 감사; 기본; R |

## 설계 보류 API와 프론트 차이

- `/returns`, `/exchanges`: 전용 상태·원판매/환불/대체품 관계가 DB에 없다. `goods_receipts.receipt_type='return'`, `logistics_orders.logistics_type='exchange'`만으로 업무 전체를 확정할 수 없다.
- `/marketplace-mappings`, `/sms-target-products`, `/integrations/bmdmall`, `/rentals`, `/expenses`: 저장 테이블/필수 필드가 없다. 새 테이블 또는 `system_settings` 사용 여부를 정한 뒤 명세화한다.
- 엑셀 다운로드는 개인정보·대량조회 권한, 비동기 내보내기, 파일 보존 기한을 정하기 전에는 엔드포인트를 확정하지 않는다. 외부 SMS 실발송도 동의·거부·공급자·재시도 정책 확정 후 분리 설계한다.
- 프론트의 `SettingsStage12.jsx`는 `settingsApi` 호출을 시도하는 구조이나 `settingsApiConfigured=false`이며 각 메서드는 예외를 던진다. `frontend/src/services/index.js`의 서비스 레지스트리는 비어 있다. 4-2에서는 요청/응답 스키마와 실제 라우터를 먼저 구현한 뒤 화면 연결을 검증한다.
