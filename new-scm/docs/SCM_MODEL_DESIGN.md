# SQLAlchemy 모델 매핑 설계

2026-10-27 `new_scm_dev.public` 읽기 전용 실측 결과 기준. 전체 52개 기본 테이블 중 ORM 업무 모델 대상은 **51개**이며 `alembic_version`은 마이그레이션 관리 테이블이라 제외한다. 컬럼 형식·NULL·기본값·PK/FK·UNIQUE·CHECK·인덱스의 전수 목록은 [SCM_DB_CATALOG.md](SCM_DB_CATALOG.md)에 있다. 실제 모델 파일이나 마이그레이션은 이 단계에서 생성하지 않았다.

## 모델 단위와 관계

모든 테이블에서 실측 `id bigint` PK를 보존한다. 아래는 코드 패키지 분리 제안이며 테이블명 변경이 아니다. 명시한 연결만 실제 FK이고, 화면상의 유사한 명칭만으로 `relationship()`을 만들지 않는다.

| 묶음 | 실제 테이블 (개수) | 관계·핵심 필드 |
|---|---|---|
| 조직·인증·감사 | `users`, `stores`, `employees`, `login_logs`, `audit_logs` (5) | `employees.store_id→stores.id`, `employees.user_id→users.id`(unique), 로그의 사용자 FK. `users.username` unique index, `password_hash`, `account_type`, `status` |
| 고객·상담·메모 | `customers`, `consultations`, `consultation_notes`, `memos` (4) | `consultations.customer_id→customers.id`, `consultation_notes.consultation_id→consultations.id`. `memos.entity_type/entity_id`는 다형 참조값이며 FK 아님 |
| A/S | `as_requests`, `as_notes`, `as_status_histories`, `as_symptom_codes`, `as_part_codes` (5) | `as_requests.customer_id→customers.id`, `product_id→products.id`, `source_consultation_id→consultations.id`(unique), 부품의 `product_id` FK |
| 상품 | `products` (1) | `product_code` unique index, `barcode` unique 제약. `serial_managed`, 가격, 안전재고 |
| 판매 | `sales`, `sale_items`, `sale_payments`, `sale_status_histories` (4) | 항목/결제/이력의 `sale_id→sales.id`; 판매의 고객·매장·직원·마켓 FK |
| 발주·입고 | `purchase_orders`, `purchase_order_items`, `purchase_order_status_histories`, `goods_receipts`, `goods_receipt_items` (5) | 발주→항목, 입고→항목, `goods_receipts.purchase_order_id`, `goods_receipt_items.purchase_order_item_id`는 선택 FK |
| 재고·이동·시리얼 | `inventory_balances`, `inventory_movements`, `inventory_adjustments`, `inventory_adjustment_items`, `stock_transfers`, `stock_transfer_items`, `stock_transfer_status_histories`, `serial_inventories`, `serial_bulk_update_jobs`, `serial_bulk_update_items`, `serial_number_corrections` (11) | 잔량 `(store_id,product_id)` unique; 원장은 실제 store/product FK와 `source_type/source_id` 비-FK; 시리얼 번호는 unique index; 수정 job→item/correction FK |
| 물류 | `logistics_orders`, `logistics_items`, `logistics_notes`, `logistics_status_histories`, `shipments` (5) | 물류의 `source_sale_id→sales.id`, `source_as_request_id→as_requests.id`는 선택 FK/partial unique; 항목·메모·이력·송장의 물류 FK |
| 공지 | `notices`, `notice_reads` (2) | `notice_reads.notice_id→notices.id`, `user_id→users.id`, `(notice_id,user_id)` unique |
| SMS | `sms_templates`, `sms_send_logs`, `sms_opt_outs` (3) | 발송 로그의 템플릿/고객 FK, 수신거부의 고객 FK. 전화 원문 대신 해시/끝 네 자리 컬럼 |
| 설정·배치 | `marketplaces`, `common_code_groups`, `common_codes`, `batch_jobs`, `batch_job_runs`, `system_settings` (6) | `common_codes.group_id→common_code_groups.id`, `batch_job_runs.batch_job_id→batch_jobs.id`, `system_settings.setting_key` unique |

## 생성·검증 전략

1. 읽기 전용 카탈로그의 형식으로 명시적 SQLAlchemy 2.x `Mapped[...]`/`mapped_column` 설계한다. `bigint→BigInteger`, `numeric(p,s)→Numeric(p,s)`/Python `Decimal`, `timestamp with time zone→DateTime(timezone=True)`, `boolean→Boolean`, `jsonb→JSONB`를 실제 컬럼별로 적용한다. Python 기본값을 DB 기본값으로 잘못 옮기지 않는다.
2. `__tablename__`과 컬럼명·NULL·server default·`ForeignKey(..., ondelete=...)`를 실측과 일치시킨다. `UniqueConstraint`, `CheckConstraint`, partial/unique index는 각각 실제 카탈로그 정의를 기준으로 매핑한다. 별도 자동 생성 도구는 **초안 생성**에만 사용한다.
3. 관계는 실제 FK에만 추가한다. 복수의 `users` FK(`created_by`, `updated_by`, `deleted_by`, 승인자 등)와 복수의 `stores` FK(출발/도착)는 `foreign_keys=`를 명시한다. DB의 `ON DELETE CASCADE/RESTRICT/SET NULL`과 ORM cascade가 충돌하지 않게 한다. `memos.entity_id`, `inventory_movements.source_id`에 가상 FK를 만들지 않는다.
4. 모델을 DB에 반영하지 않고 `inspect(engine)`과 모델 `MetaData`를 **비파괴 비교**한다. 컬럼명/형식/NULL/기본값/제약/인덱스 차이를 0건으로 만든 후 API에 사용한다. `metadata.create_all`, Alembic `upgrade`, `--autogenerate` 적용은 별도 변경 절차가 필요하다.
5. 응답 스키마는 ORM 엔터티와 분리한다. `users.password_hash`, `sms_opt_outs.normalized_phone_hash`, `sms_send_logs.recipient_phone_hash`, `audit_logs.before_data/after_data`는 기본 응답에서 제외하고 권한별 마스킹한다.

## 실측 구조와 화면/코드의 불일치

- 백엔드에는 현재 ORM 모델, 업무 라우터, 쓰기 DB 세션이 없다. `app/db/database.py`는 `new_scm_dev`만 허용하는 읽기 전용 진단 연결이다. 화면의 `useState`/Mock 레코드는 DB 행이 아니다.
- `SettingsManagement.jsx`의 마켓별 Excel 매핑 규칙(`headerStart`, `dataStart`, 컬럼 문자 등)은 `marketplaces` 또는 별도 테이블에 없다. `/settings/target-products`의 사용일수/SMS 사용 설정도 `products`에 없다. BMDMALL 전용 설정·대여·지출결의·반품/교환의 원판매 연계 테이블도 없다. 신규 테이블/컬럼이 필요한지 업무 규칙을 확인해야 한다.
- 화면의 `지역`과 `stores` 컬럼은 1:1이 아니다(`address`만 존재). 구형 증상 화면의 브랜드/체크타입 필드는 `as_symptom_codes`의 실제 컬럼과 일치하지 않는다. API 요청에 해당 필드를 그대로 쓰면 안 된다.
- `users.account_type`은 `admin|employee`, `status`는 `active|suspended` CHECK다. 메뉴별 권한과 세션/토큰 테이블은 없다. `password_hash`의 저장 **형식/알고리즘은 스키마만으로 알 수 없으므로** 실데이터를 출력하거나 임의 가정하지 않고 인증 구현 전에 별도 확인한다.
- 현재 고객/상품/판매/A/S 코드와 `serial_inventories.serial_number`는 **unique index가 실제 존재**한다. 기존 분석의 “중복 방지 제약 필요”는 현 DB에서는 일반 코드·시리얼 컬럼에 대해 해소됐으나, 코드 생성의 경쟁 조건·대소문자/공백 정규화 정책은 별도다. [위험 분석](SCM_GAP_ANALYSIS.md)을 참조한다.

## 우선순위

P0: `users`/인증·감사·권한 경계, P1: 기준정보와 핵심 거래 모델/원자 처리, P2: SMS·배치·시리얼 일괄 수정·통계. 자동 생성된 코드는 실측 비교 전까지 최종 모델이 아니다.
