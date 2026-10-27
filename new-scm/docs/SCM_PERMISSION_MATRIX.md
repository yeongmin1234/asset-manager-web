# 신규 SCM 권한 매트릭스 (4-2단계)

2026-10-27 기준. 4-1 설계의 표시 경로 39개·업무 API 제안 115개를 매핑했다. **제안 목록이며 업무 API 115개는 아직 구현되지 않았다.**

## 정책

- 서버의 검증된 사용자에게 `system.access`가 명시적으로 부여되어야 한다. 기본 grant는 비어 있으며 `users.account_type=admin`만으로 권한을 얻지 않는다.
- 아래 `POST /auth/login`은 4-1 카탈로그의 과거 제안 항목이며 독립 SCM 로그인 화면/API를 구현한다는 뜻이 아니다. 4-2A에서는 기존 통합 로그인 인계 계약이 마련될 때까지 인증을 거부한다.
- 메뉴 grant는 화면 경로와 분리하고, API action grant는 각 엔드포인트에서 별도 검사한다. 메뉴가 보인다는 이유로 API 사용을 허용하지 않는다.
- 관리자 기능은 활성 사용자 + `system.access` + `account_type=admin` + `admin.manage`를 함께 요구한다. 기존 `users`에는 grant 저장 컬럼/테이블이 없다.
- 매장/고객/개인정보의 행·필드별 범위, 승인자 분리, 상태 전이, 업로드·일괄 변경은 API 구현 전에 별도 서버 정책을 확정해야 한다.
- 아래 API의 관련 화면은 탐색용 대응이다. API 허가는 해당 화면 grant와 독립이다. 숨김/404 화면도 기본 거부다.

## 메뉴 경로 39개

| 화면 | 경로 (메뉴 grant 후보) | 추가 조건 | 현재 상태 |
|---|---|---|---|
| HOME | `/` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 직원리스트 | `/store-management/staff` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 상품등록 | `/store-management/products` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 매장리스트 | `/store-management/stores` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 매장 통계 | `/store-management/statistics` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 매장 공지 | `/store-management/notices` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 고객상담 기본 | `/customer-consulting` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| A/S 접수 | `/customer-consulting/as-reception` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 판매 접수 | `/customer-consulting/sales-reception` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 상담목록 탭 | `/customer-consulting/consultation-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 반품목록 | `/customer-consulting/return-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 교환목록 | `/customer-consulting/exchange-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| A/S 목록 탭 | `/customer-consulting/as-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 판매목록 탭 | `/customer-consulting/sales-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 입출고목록 | `/customer-consulting/logistics-list` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 입출고관리 | `/customer-consulting/logistics-management` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 고객관리 | `/customers` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 상담목록 | `/consultations` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| A/S | `/as` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 판매 | `/sales` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 물류 | `/logistics` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 발주지원센터 | `/order-support` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 공지사항 | `/notices` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 메모검색 | `/memo-search` | `system.access` + 명시적 경로 grant | 매핑 제안; 서버 업무 API 미구현 |
| 환경설정 첫 화면 | `/settings` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 공통/기본 설정 | `/settings/general` | 관리자 + `admin.manage`; 현재 404 | 매핑 제안; 서버 업무 API 미구현 |
| 계정관리 | `/settings/accounts` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 코드관리 | `/settings/codes` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 배치관리 | `/settings/batches` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 마켓 | `/settings/markets` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 데이터 매핑 | `/settings/data-mapping` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| A/S 설정 | `/settings/as` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 증상/파트관리 | `/settings/symptoms` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 필터교체 SMS | `/settings/filter-sms` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 발송현황 | `/settings/send-status` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 수신거부 지정 | `/settings/opt-out` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 대상 제품관리 | `/settings/target-products` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| BMDMALL | `/settings/bmdmall` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |
| 시리얼번호 업데이트 | `/settings/serial-update` | 관리자 + `admin.manage` | 매핑 제안; 서버 업무 API 미구현 |

## 업무 API 제안 115개

| Method | Endpoint | 관련 화면 | API action grant | 추가 검증 | 상태 |
|---|---|---|---|---|---|
| POST | `/auth/login` | `미정` | `public (4-1 제안; 이번 단계 미구현)` | 공개 | 미구현 |
| POST | `/auth/logout` | `미정` | `auth.logout` | 로그인 | 미구현 |
| GET | `/auth/me` | `미정` | `system.access` | 로그인 | 공통 API 구현; 검증기 미연결로 401 |
| GET | `/users` | `/settings/accounts` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| GET | `/users/{id}` | `/settings/accounts` | `data.read` | 관리 또는 본인 | 미구현 |
| POST | `/users` | `/settings/accounts` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/users/{id}` | `/settings/accounts` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| POST | `/users/{id}/password-reset` | `/settings/accounts` | `data.create` | 관리/본인 | 미구현 |
| GET | `/stores` | `/store-management/stores` | `data.read` | 조회 | 미구현 |
| GET | `/stores/{id}` | `/store-management/stores` | `data.read` | 조회 | 미구현 |
| POST | `/stores` | `/store-management/stores` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/stores/{id}` | `/store-management/stores` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/employees` | `/store-management/staff` | `data.read` | 조회 | 미구현 |
| GET | `/employees/{id}` | `/store-management/staff` | `data.read` | 조회 | 미구현 |
| POST | `/employees` | `/store-management/staff` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/employees/{id}` | `/store-management/staff` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| POST | `/employees/{id}/resignation` | `/store-management/staff` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| GET | `/marketplaces` | `/settings/markets` | `data.read` | 조회 | 미구현 |
| POST | `/marketplaces` | `/settings/markets` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/marketplaces/{id}` | `/settings/markets` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/code-groups` | `/settings/codes` | `data.read` | 조회 | 미구현 |
| POST | `/code-groups` | `/settings/codes` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/code-groups/{id}` | `/settings/codes` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/code-groups/{id}/codes` | `/settings/codes` | `data.read` | 조회 | 미구현 |
| POST | `/code-groups/{id}/codes` | `/settings/codes` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/codes/{id}` | `/settings/codes` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/system-settings` | `/settings` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/system-settings/{id}` | `/settings` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/customers` | `/customers` | `data.read` | 조회 | 미구현 |
| GET | `/customers/{id}` | `/customers` | `data.read` | 담당 | 미구현 |
| POST | `/customers` | `/customers` | `data.create` | 담당 | 미구현 |
| PATCH | `/customers/{id}` | `/customers` | `data.update` | 담당 | 미구현 |
| DELETE | `/customers/{id}` | `/customers` | `data.delete` | 관리자 + `admin.manage` | 미구현 |
| GET | `/customers/{id}/history` | `/customers` | `data.read` | 담당 | 미구현 |
| GET | `/consultations` | `/consultations` | `data.read` | 조회 | 미구현 |
| GET | `/consultations/{id}` | `/consultations` | `data.read` | 담당 | 미구현 |
| POST | `/consultations` | `/consultations` | `data.create` | 담당 | 미구현 |
| PATCH | `/consultations/{id}` | `/consultations` | `data.update` | 담당 | 미구현 |
| POST | `/consultations/{id}/status` | `/consultations` | `status.change` | 담당 | 미구현 |
| POST | `/consultations/{id}/notes` | `/consultations` | `data.create` | 담당 | 미구현 |
| GET | `/as-requests` | `/as` | `data.read` | 조회 | 미구현 |
| GET | `/as-requests/{id}` | `/as` | `data.read` | 담당 | 미구현 |
| POST | `/as-requests` | `/as` | `data.create` | 담당 | 미구현 |
| PATCH | `/as-requests/{id}` | `/as` | `data.update` | 담당 | 미구현 |
| POST | `/as-requests/{id}/status` | `/as` | `status.change` | 담당 | 미구현 |
| POST | `/as-requests/{id}/notes` | `/as` | `data.create` | 담당 | 미구현 |
| GET | `/as-symptoms` | `/settings/symptoms` | `data.read` | 조회 | 미구현 |
| POST | `/as-symptoms` | `/settings/symptoms` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/as-symptoms/{id}` | `/settings/symptoms` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/as-parts` | `/settings/symptoms` | `data.read` | 조회 | 미구현 |
| POST | `/as-parts` | `/settings/symptoms` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/as-parts/{id}` | `/settings/symptoms` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/products` | `/store-management/products` | `data.read` | 조회 | 미구현 |
| GET | `/products/{id}` | `/store-management/products` | `data.read` | 조회 | 미구현 |
| POST | `/products` | `/store-management/products` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/products/{id}` | `/store-management/products` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/sales` | `/sales` | `data.read` | 조회 | 미구현 |
| GET | `/sales/{id}` | `/sales` | `data.read` | 담당 | 미구현 |
| POST | `/sales` | `/sales` | `data.create` | 담당 | 미구현 |
| PATCH | `/sales/{id}` | `/sales` | `data.update` | 담당 | 미구현 |
| POST | `/sales/{id}/payments` | `/sales` | `data.create` | 담당 | 미구현 |
| POST | `/sales/{id}/status` | `/sales` | `status.change` | 담당 | 미구현 |
| GET | `/purchase-orders` | `/order-support` | `data.read` | 조회 | 미구현 |
| GET | `/purchase-orders/{id}` | `/order-support` | `data.read` | 담당 | 미구현 |
| POST | `/purchase-orders` | `/order-support` | `data.create` | 담당 | 미구현 |
| PATCH | `/purchase-orders/{id}` | `/order-support` | `data.update` | 담당 | 미구현 |
| POST | `/purchase-orders/{id}/status` | `/order-support` | `approval.grant` | 별도 승인자 + 자기 승인 금지 | 미구현 |
| GET | `/goods-receipts` | `/customer-consulting/logistics-list` | `data.read` | 조회 | 미구현 |
| GET | `/goods-receipts/{id}` | `/customer-consulting/logistics-list` | `data.read` | 담당 | 미구현 |
| POST | `/goods-receipts` | `/customer-consulting/logistics-list` | `data.create` | 담당 | 미구현 |
| POST | `/goods-receipts/{id}/complete` | `/customer-consulting/logistics-list` | `status.change` | 담당 | 미구현 |
| GET | `/inventory-balances` | `/customer-consulting/logistics-list` | `data.read` | 조회 | 미구현 |
| GET | `/inventory-movements` | `/customer-consulting/logistics-list` | `data.read` | 조회 | 미구현 |
| GET | `/serial-inventories` | `/customer-consulting/logistics-list` | `data.read` | 조회 | 미구현 |
| GET | `/stock-transfers` | `/customer-consulting/logistics-management` | `data.read` | 조회 | 미구현 |
| POST | `/stock-transfers` | `/customer-consulting/logistics-management` | `data.create` | 담당 | 미구현 |
| POST | `/stock-transfers/{id}/status` | `/customer-consulting/logistics-management` | `approval.grant` | 별도 승인자 + 자기 승인 금지 | 미구현 |
| GET | `/inventory-adjustments` | `/customer-consulting/logistics-management` | `data.read` | 조회 | 미구현 |
| POST | `/inventory-adjustments` | `/customer-consulting/logistics-management` | `data.create` | 담당 | 미구현 |
| POST | `/inventory-adjustments/{id}/apply` | `/customer-consulting/logistics-management` | `approval.grant` | 별도 승인자 + 자기 승인 금지 | 미구현 |
| GET | `/logistics-orders` | `/logistics` | `data.read` | 조회 | 미구현 |
| GET | `/logistics-orders/{id}` | `/logistics` | `data.read` | 담당 | 미구현 |
| POST | `/logistics-orders` | `/logistics` | `data.create` | 담당 | 미구현 |
| POST | `/logistics-orders/{id}/status` | `/logistics` | `status.change` | 담당 | 미구현 |
| POST | `/logistics-orders/{id}/shipments` | `/logistics` | `data.create` | 담당 | 미구현 |
| POST | `/logistics-orders/{id}/notes` | `/logistics` | `data.create` | 담당 | 미구현 |
| GET | `/notices` | `/notices` | `data.read` | 조회 | 미구현 |
| GET | `/notices/{id}` | `/notices` | `data.read` | 조회 | 미구현 |
| POST | `/notices` | `/notices` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/notices/{id}` | `/notices` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| POST | `/notices/{id}/read` | `/notices` | `notice.read` | 로그인 | 미구현 |
| GET | `/memos` | `/memo-search` | `data.read` | 조회 | 미구현 |
| POST | `/memos` | `/memo-search` | `data.create` | 담당 | 미구현 |
| PATCH | `/memos/{id}` | `/memo-search` | `data.update` | 담당 | 미구현 |
| DELETE | `/memos/{id}` | `/memo-search` | `data.delete` | 작성자/관리자 | 미구현 |
| GET | `/sms-templates` | `/settings/filter-sms` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| POST | `/sms-templates` | `/settings/filter-sms` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| PATCH | `/sms-templates/{id}` | `/settings/filter-sms` | `data.update` | 관리자 + `admin.manage` | 미구현 |
| GET | `/sms-send-logs` | `/settings/send-status` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| POST | `/sms/dry-run` | `/settings/filter-sms` | `sms.dry_run` | 관리자 + `admin.manage` | 미구현 |
| GET | `/sms-opt-outs` | `/settings/opt-out` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| POST | `/sms-opt-outs` | `/settings/opt-out` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| POST | `/sms-opt-outs/{id}/revoke` | `/settings/opt-out` | `data.create` | 관리자 + `admin.manage` | 미구현 |
| GET | `/batch-jobs` | `/settings/batches` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| GET | `/batch-jobs/{id}/runs` | `/settings/batches` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| POST | `/batch-jobs/{id}/runs` | `/settings/batches` | `batch.run` | 관리자 + `admin.manage` | 미구현 |
| GET | `/serial-bulk-jobs` | `/settings/serial-update` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| GET | `/serial-bulk-jobs/{id}` | `/settings/serial-update` | `data.read` | 관리자 + `admin.manage` | 미구현 |
| POST | `/serial-bulk-jobs` | `/settings/serial-update` | `excel.upload` | 관리자 + `admin.manage` | 미구현 |
| POST | `/serial-bulk-jobs/{id}/validate` | `/settings/serial-update` | `bulk.change` | 관리자 + `admin.manage` | 미구현 |
| POST | `/serial-bulk-jobs/{id}/approve` | `/settings/serial-update` | `approval.grant` | 별도 승인자 + 자기 승인 금지 | 미구현 |
| POST | `/serial-bulk-jobs/{id}/apply` | `/settings/serial-update` | `approval.grant + bulk.change` | 별도 승인자 + 자기 승인 금지 | 미구현 |
| GET | `/dashboard/summary` | `/` | `data.read` | 조회 | 미구현 |
| GET | `/reports/store-sales` | `/store-management/statistics` | `data.read` | 조회 | 미구현 |
| GET | `/audit-logs` | `/activity` | `audit.read` | 관리자 + `admin.manage` | 미구현 |

## 실제 구현과 저장소 제약

- 구현된 인증 API: `GET /api/v1/auth/me` 1개. 현재 검증기가 미연결이므로 실제 호출은 401이다. 테스트 주입으로만 200/403 경계를 확인했다.
- 구현된 서버 공통 검사: 활성 검증 사용자, `system.access`, 독립 메뉴 grant, 독립 action grant, 관리자 이중 조건. 업무 API 라우터가 없어 115개 엔드포인트별 검사 실행은 0개다.
- `users(id,username,name,email,password_hash,account_type,status,...)`에는 세부 권한과 외부 통합 사용자 연결 키가 없다. 새 테이블/컬럼을 만들지 않았다.
- 후속 스키마 제안: 외부 주체와 SCM 사용자 매핑(유일 키·활성 여부), 역할/사용자별 메뉴·action grant, 매장 범위, 승인 분리, 변경 감사. 설계 승인 전 마이그레이션 금지.
