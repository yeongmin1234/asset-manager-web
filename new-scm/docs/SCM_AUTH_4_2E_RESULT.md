# 신규 SCM 4-2E 결과 (2026-10-27)

## 판정

**DB 구조 및 코드 작성 완료, 실제 DB 적용·사용자 등록 대기.** `new_scm_dev`에는 마이그레이션을 적용하지 않았다. 따라서 DB 구축 완료나 실제 통합 로그인 성공으로 판정하지 않는다. 4-2F의 인증 전제 기능은 DB 적용과 승인된 사용자 매핑 뒤에 검증 가능하다.

## 1. 실제 DB 구조와 재사용

`127.0.0.1:5432/new_scm_dev`에 `new_scm_ro`로 접속하고 읽기 전용 트랜잭션에서 카탈로그와 행 수만 확인했다. DB·계정·읽기 전용 상태를 먼저 검증했다. Alembic 버전은 `20260729_0012`, 기본 테이블은 52개다. 인증 관련 테이블은 `users`(2행)와 `login_logs`(8행)이며, 역할·권한·외부 사용자 매핑 테이블은 없다. 실제 사용자 값은 출력하거나 변경하지 않았다.

| 재사용 대상 | 확인한 구조 | 4-2E 용도 |
| --- | --- | --- |
| `users` | `id bigint` PK, `status` active/suspended, `account_type` admin/employee, `username` unique 인덱스, `email` unique 제약 | 매핑 FK, 활성 상태·관리자 유형 검사 |
| `login_logs` | `id` PK, `user_id` FK `ON DELETE SET NULL`, 결과 CHECK, 조회 인덱스 | 기존 로그인 기록 보존. 권한 저장소로는 부적합 |
| `alembic_version` | `version_num` PK, 현재 `20260729_0012` | 후속 revision 연결 |

`users`와 `alembic_version`의 소유자는 `new_scm_app`이다. 해당 역할의 `CONNECT`·`public CREATE`·버전 테이블 `UPDATE` 실효 권한은 확인했으나, 마이그레이션 접속 정보와 이 역할 사용 승인은 확인되지 않았다. `new_scm_ro`는 대상 업무 테이블 SELECT 가능, INSERT 및 DB·스키마 CREATE 불가를 확인했다. 기존 `users`의 PK, UNIQUE, CHECK, 데이터는 변경하지 않는다.

## 2. 추가 구조 (작성 완료, 미적용)

`backend/alembic/versions/20261027_0013_scm_identity_grants.py`를 기존 버전 `20260729_0012`의 후속으로 작성했다. 저장소에 기존 Alembic revision 파일이 없어, 실제 기존 스키마를 생성하거나 수정하지 않는 기준점 revision도 함께 넣었다. 새 DB의 전체 부트스트랩은 이 migration 체계의 범위 밖이다.

| 테이블 | 주요 제약 | 상태 |
| --- | --- | --- |
| `scm_identity_mappings` | `(issuer,subject)` UNIQUE, `user_id` UNIQUE·`users.id` FK, 양의 ASCII 십진 ID CHECK, 활성 매핑 승인자/승인일 필수 | migration 작성, DB 미적용 |
| `scm_user_grants` | `(user_id,grant_type,grant_name)` PK, 사용자·승인자 FK, menu/action CHECK, 비어 있지 않은 권한명 | migration 작성, DB 미적용 |

마이그레이션은 두 테이블에만 `new_scm_ro` SELECT를 부여한다. 기본 매핑은 비활성이며 기본 grant는 없다. `system.access`, `admin.manage`, 메뉴 경로와 `data.read` 등의 action 키는 [권한 매트릭스](SCM_PERMISSION_MATRIX.md)와 기존 코드의 정확한 문자열을 사용한다. 요청서의 `customers.read`, `products.create` 같은 값은 현재 매트릭스의 실제 키가 아니므로 추가하지 않았다. Down migration은 두 테이블과 안의 데이터를 **영구 삭제**하므로 실제 매핑 등록 뒤에는 복구 계획 없이 실행하면 안 된다.

## 3. 백엔드 연동

- 기존 인증 서버의 `user.id`를 문자열화한 양의 ASCII 십진 ID만 `subject`로 허용한다. 사용자명·이메일·같은 숫자 ID로 SCM 계정을 자동 연결하지 않는다.
- `app/db/identity.py`가 활성 매핑, 활성 `users`, 명시적 grant를 읽는다. `handoff.py`는 이 저장소로 Principal을 만든다. 매핑 없음·비활성·사용자 중지는 세션 발급 전에 403으로 거부한다. `system.access`가 없으면 403이다.
- 세션은 30분 만료이며 매 요청에서 DB 매핑·grant를 다시 읽는다. 권한 회수·계정 중지는 다음 요청에 반영된다. 무세션은 401, 세션 중 매핑 해제는 403이다. DB 조회 오류는 세션을 발급하지 않으며 내부 오류를 응답에 노출하지 않는다.
- 관리자 기능은 `account_type=admin`과 `admin.manage`를 모두 요구한다. 프론트엔드의 메뉴 검사는 기존 `canAccessPath`가 서버에서 받은 menu grant를 사용한다. 업무 API는 아직 없으므로 4-2F에서 각 라우트에 `require_permission`을 붙여야 한다.

## 4. 마이그레이션 안전 상태와 적용 절차

현재 `new_scm_ro`로만 접속했으며 백업을 만들거나 DB를 변경하지 않았다. 승인된 마이그레이션 자격정보가 없으므로 적용 조건을 충족하지 않는다. `backend/alembic/env.py`는 별도 `SCM_MIGRATION_DATABASE_URL`, 역할명, 비어 있지 않은 백업 파일을 요구하며 `127.0.0.1:5432/new_scm_dev`와 쓰기 가능한 실제 세션을 검증한다. 앱의 읽기 전용 URL을 재사용하지 않는다.

적용 전 관리자가 수행할 절차:

1. `new_scm_app`을 마이그레이션 역할로 사용할 승인을 확인하거나, 별도 신규 SCM 전용 역할을 마련한다. 현재 역할의 소유권·권한만 확인됐고 사용 승인은 확인되지 않았다. 역할 생성이나 권한 상승이 필요하면 대상 DB 소유자가 범위를 검토하고 수행한다. `new_scm_ro`의 쓰기 권한은 늘리지 않는다.
2. **직접 DB명을 확인한 후** `pg_dump -h 127.0.0.1 -p 5432 -U <승인된_역할> -W -d new_scm_dev -Fc -f <보호된_절대_백업_경로>`를 실행한다. 백업 파일이 0바이트가 아니고 `pg_restore -l <백업_경로>`가 성공하는지 확인한다. 백업은 저장소 밖에 보관하고 복구 절차를 확인한다.
3. `deploy/auth_4_2e_verify.sql`을 실행하여 현재 버전 `20260729_0012`, 기존 두 인증 테이블, 신규 두 테이블 부재를 확인한다. 실제 구조를 위 표와 대조한다. 충돌·불일치 시 중단한다.
4. 일회성 셸 환경에 `SCM_MIGRATION_DATABASE_URL`(승인된 역할 URL), `SCM_MIGRATION_ROLE`, `SCM_MIGRATION_BACKUP_PATH`를 설정한다. 비밀번호는 명령행·문서·Git에 기록하지 않는다. 저장소 `new-scm`에서 `python -m alembic -c backend/alembic.ini upgrade head`를 실행한다. 백업 실패, 대상 DB 불일치, 권한 불명확, revision 충돌 시 실행하지 않는다.
5. 같은 검증 SQL을 다시 실행한다. 기대값: revision `20261027_0013`, 총 기본 테이블 54개, 신규 테이블 2개, `new_scm_ro` SELECT=true·INSERT=false. `users` 행 수와 `login_logs` 행 수가 적용 전과 같은지도 비교한다. 매핑과 grant는 0행이어야 한다.

실제 사용자 매핑과 `system.access` 부여는 별도 승인 사항이다. 승인 시 기존 인증 서버의 실제 `/auth/me.id` 소유자와 SCM `users.id`를 각각 확인하고, 별도 관리자 승인자로 기록한 뒤 매핑을 활성화한다. 사용자명·이메일 추정이나 임의 관리자 생성은 하지 않는다. 변경은 승인된 SCM 전용 쓰기 역할이 처리해야 하며 `new_scm_ro`를 사용하지 않는다.

## 5. 테스트와 영향

- 백엔드 단위·격리 SQL 테스트 **26개 통과, 0개 실패**. 매핑 유무·중복·FK·비활성, grant 부여·회수, 메뉴·action·관리자 분리, DB 오류, 세션 발급 경계를 포함한다. 격리 SQL 테스트는 SQLite 메모리 DB를 사용했으며 PostgreSQL migration 실제 적용 검증을 대신하지 않는다.
- Alembic revision 체인과 PostgreSQL dialect용 upgrade SQL 생성 확인: CREATE TABLE 2개, FK 4개, RO SELECT grant 포함. 실제 PostgreSQL 실행 결과는 없다.
- 변경은 `new-scm` 내부 코드·문서에만 있다. 기존 자산관리 코드·DB, MySQL, NAS, 보호 포트와 서비스는 변경하지 않았다.

**4-2F 진행:** 인증 없는 업무 API 구현과 권한 의존성 연결은 진행 가능하다. 실제 사용자 세션을 이용한 통합 검증은 migration 적용과 승인된 매핑·grant 이후에 진행한다.
