# [4-2E 최종 결과] 2026-10-27

## 판정

**DB 적용 중단.** 전체 DB 백업이 실패했으므로 `20261027_0013` 마이그레이션은 실행하지 않았다. 신규 매핑·권한 테이블 및 실제 사용자 권한은 아직 없다. 4-2F의 실제 통합 로그인 검증은 진행할 수 없다.

## 1. 확인 결과

| 항목 | 실제 결과 |
| --- | --- |
| DB 연결 확인 | `new_scm_ro`로 `127.0.0.1:5432/new_scm_dev` 접속. `transaction_read_only=on` 확인 |
| 백업 완료 여부 | **실패**. `pg_dump -Fc`가 `public.as_code_seq`의 `last_value, is_called` 조회 권한 부족으로 종료 코드 1 반환. 생성된 불완전 덤프는 삭제했고 유효한 백업 파일은 없음 |
| 백업 복구 검증 여부 | 미실시. 검증할 백업 파일이 없음 |
| 마이그레이션 계정 및 권한 | DB 역할 `new_scm_app`은 존재하나 사용 승인·접속 자격정보는 확인되지 않음. 현재 셸과 신규 SCM `.env`에 전용 마이그레이션 설정 없음. `new_scm_ro`는 `users` SELECT 가능, INSERT·DB CREATE·스키마 CREATE 불가 |
| Alembic 적용 전 버전 | `20260729_0012` |
| Alembic 적용 후 버전 | `20260729_0012` (변경 없음) |
| 신규 테이블 생성 여부 | `scm_identity_mappings`, `scm_user_grants` 모두 없음 |
| 사용자 매핑 테이블 상태 | 마이그레이션 파일에만 정의, DB 미적용 |
| 권한 저장 테이블 상태 | 마이그레이션 파일에만 정의, DB 미적용 |
| 기존 데이터 보존 여부 | 작업 전 `users` 2행, `login_logs` 8행, `public` 기본 테이블 52개 확인. DB 쓰기를 하지 않았으므로 이 작업으로 인한 변경 없음. 작업 후 DB 재조회는 하지 않음 |
| `new_scm_ro` SELECT 확인 | 기존 `users` SELECT 확인. 신규 테이블은 존재하지 않아 확인 불가 |
| 실제 사용자 매핑 여부 | 없음. 통합 로그인 고유 ID와 SCM 사용자 ID를 검증한 후보도 없음 |
| 실제 권한 부여 여부 | 없음. `system.access`를 포함한 grant 미등록 |
| 테스트 통과·실패 건수 | 로컬 `unittest` 26개 통과, 0개 실패. PostgreSQL 마이그레이션·Repository 실연결 테스트는 미실시. 테스트 실행 중 AnyIO `ResourceWarning` 발생 |
| 기존 자산관리 영향 여부 | 해당 코드·DB·환경설정에 접근하거나 변경하지 않음 |
| NAS 및 보호 포트 영향 여부 | 서비스 실행·재시작·배포·포트 변경 없음 |
| 4-2F 진입 가능 여부 | 실제 통합 로그인 검증은 불가. DB 구조 적용과 승인된 사용자 등록이 선행되어야 함 |
| 미완료 항목 및 필요한 사용자 조치 | 아래 백업 권한 보완, 검증된 백업, 승인된 마이그레이션 계정, DB 적용, 사용자 매핑·권한 별도 승인 |

## 2. 마이그레이션 사전 검토

`backend/alembic/versions/20261027_0013_scm_identity_grants.py`의 `down_revision`은 현재 버전 `20260729_0012`와 일치한다. 신규 테이블 두 개에만 DDL을 수행하며 기존 `users`를 FK로 참조한다. 기존 업무 테이블을 삭제하거나 수정하지 않는다. 현재 DB에는 두 테이블이 없어 이름 충돌이 없다. 매핑 테이블에는 PK, `(issuer, subject)` 및 `user_id` UNIQUE, 사용자·승인자 FK, 활성 매핑 승인 정보 CHECK, 기본 `is_active=false`가 있다. 권한 테이블에는 `(user_id, grant_type, grant_name)` PK, 사용자·승인자 FK, 권한 유형 CHECK가 있다. PK·UNIQUE 제약이 조회용 인덱스를 제공한다. 매핑의 생성·수정 시각과 grant의 승인 시각에는 서버 기본값이 정의되어 있다. 매핑 승인 시각은 활성화 전에 명시해야 한다. 권한 코드는 문자열로 보관하며 기본 grant는 없다. 마이그레이션은 새 테이블에만 `new_scm_ro` SELECT를 부여한다. Python 구문 컴파일과 SQLAlchemy/Alembic 패키지 로딩은 성공했다. PostgreSQL 실제 적용과 FK·GRANT 동작은 검증하지 못했다.

## 3. 백업 실패 원인과 보완 절차

`pg_dump`는 `new_scm_ro`로 전체 `new_scm_dev`의 custom-format 백업을 시도했다. 비밀번호는 실행 인수나 출력에 넣지 않았다. `public.as_code_seq`의 현재 값을 읽는 단계에서 권한 부족으로 실패했다. 이는 전체 복구 가능한 백업을 확보하지 못했다는 뜻이다. 다른 시퀀스도 같은 권한 부족이 있을 수 있으므로 첫 실패만 고치고 완료로 간주해서는 안 된다.

DB 소유자 또는 해당 시퀀스의 권한 부여자가 DBeaver에서 **반드시 `127.0.0.1:5432/new_scm_dev` 연결을 선택**하고 다음 읽기 전용 진단 SQL을 실행한다. 결과를 검토한 뒤 `new_scm_ro`에 필요한 시퀀스의 `SELECT`만 부여한다. `USAGE`나 `UPDATE`는 백업 목적에 필요하지 않다.

```sql
SELECT current_database(), current_user,
       inet_server_addr(), inet_server_port();

SELECT n.nspname AS schema_name, c.relname AS sequence_name,
       has_sequence_privilege('new_scm_ro', c.oid, 'SELECT') AS can_select
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'S'
ORDER BY c.relname;

-- 확인된 첫 실패를 보완하는 최소 권한 예시. 권한 부여자가 실행한다.
GRANT SELECT ON SEQUENCE public.as_code_seq TO new_scm_ro;
```

다른 시퀀스에도 `can_select=false`가 있으면 소유자와 범위를 확인하고 필요한 대상에만 같은 `GRANT SELECT ON SEQUENCE`를 적용한다. DBeaver에서 자동 커밋 설정과 실행 결과를 확인한다. `new_scm_ro`에는 쓰기 권한을 부여하지 않는다. 그 뒤 백업을 처음부터 다시 생성하고 파일 크기, `PGDMP` 형식 서명, `pg_restore -l`의 DB 이름과 종료 코드, 아카이브 항목을 확인한다. 백업 파일은 Git 밖의 제한된 로컬 경로에 저장한다. 비밀번호는 명령줄·문서·로그에 넣지 않는다.

복구 가능성 검증은 승인된 격리 PostgreSQL 인스턴스의 빈 테스트 DB에 `pg_restore`로 전체 복원한 뒤 테이블·행 수·Alembic 버전을 대조한다. 현재 `new_scm_dev`에는 시험 복원을 하지 않는다. 실제 사고 복구 시에는 SCM 쓰기 중지, 대상 DB 식별, 별도 복구 승인, 빈 DB 복원, 데이터 검증 순으로 진행한다. 이번에는 유효한 백업이 없어 복구 시험도 하지 않았다.

## 4. 마이그레이션 재개 조건

1. 위 백업과 `pg_restore -l` 검증을 완료하고, 가능하면 격리 복원도 확인한다.
2. `new_scm_app` 사용을 승인하고 별도 제공된 자격정보로 접속할 수 있는지 확인하거나, 신규 SCM 전용 마이그레이션 역할을 DB 소유자가 마련한다. 관리자 권한이나 `new_scm_ro` 권한을 임의로 높이지 않는다.
3. DBeaver에서 승인된 역할로 `new_scm_dev` 연결을 선택한다. `SELECT current_database(), current_user, current_setting('transaction_read_only');`로 대상·역할·쓰기 가능 상태를 확인한다. `new_scm_app`을 쓸 경우 기존 `users`·`alembic_version` 소유권과 `public` 스키마 CREATE 권한을 확인한다. 별도 역할을 쓸 경우 DB 소유자가 `CONNECT`, `public`의 `USAGE, CREATE`, `users(id)`의 `REFERENCES`, `alembic_version`의 Alembic 버전 변경 권한, 생성 테이블에 `new_scm_ro` SELECT를 부여할 수 있는 권한을 점검한다. 필요한 GRANT는 소유자가 해당 객체에만 적용한다.
4. 적용 직전 읽기 전용으로 revision, 52개 테이블, 신규 두 테이블 부재, 기존 테이블별 행 수를 다시 기록한다. 예상과 다르면 중단한다.
5. 승인된 마이그레이션 URL·역할명·검증된 백업 경로를 일회성 `SCM_MIGRATION_DATABASE_URL`, `SCM_MIGRATION_ROLE`, `SCM_MIGRATION_BACKUP_PATH`에 설정하고 `new-scm`에서 `python -m alembic -c backend/alembic.ini upgrade 20261027_0013`을 실행한다. 비밀번호를 명령행에 쓰지 않는다.
6. `deploy/auth_4_2e_verify.sql`과 읽기 전용 조회로 revision `20261027_0013`, 총 54개 테이블, PK·FK·UNIQUE·CHECK, 신규 테이블 0행, 기존 테이블별 행 수 동일, `new_scm_ro` 신규 테이블 SELECT 가능·INSERT 불가를 확인한다. 인증 Repository의 실제 DB 조회도 확인한다.
7. 기존 통합 로그인 고유 ID와 SCM `users.id`의 소유자를 검증한 뒤에만 매핑 후보와 최소 `system.access` 권한안을 작성한다. 실제 매핑 활성화와 권한 부여에는 별도 사용자 승인이 필요하다. 이름·이메일 일치로 자동 연결하지 않는다.

이번 작업에서 DB에 실행한 문장은 SELECT뿐이며, 백업 시도와 로컬 테스트 외에 서비스 작업은 없었다.
