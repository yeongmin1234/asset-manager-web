# 신규 SCM 4-2I 사전 검증 결과 및 승인 절차

검증일: 2026-10-28 (KST). 기존 미커밋 4-2H 변경을 유지하고 중단된 4-2I 수정에서 이어 진행했다. NAS SSH/서비스/DB에는 접속하거나 변경하지 않았으며 실제 NAS 컨테이너 실행·배포·마이그레이션·Commit·Push는 수행하지 않았다.

## 완료 / 미완료 / 승인 필요

| 상태 | 항목 |
|---|---|
| 완료 | 독립 로그인/로그아웃/세션/권한/쿠키/Origin CSRF 방어 분석 및 로컬 회귀 |
| 완료 | 마이그레이션 전·후 preflight 분리, 고정 PASS/FAIL/PENDING 및 exit 상태 검증 |
| 완료 | 로컬 실제 PostgreSQL에서 Alembic 명령으로 0014 적용, DDL 중간 실패 롤백 및 재적용 |
| 완료 | 적용 전·후 custom 백업을 각각 새 격리 DB에 복구, public 54개 및 인증 3개 테이블의 데이터·구조·권한·시퀀스 비교 |
| 완료 | 최소 권한/RO 유지/초기 관리자 숨김 입력/미승인 사용자 차단 검사 |
| 완료 | Compose 2.20.1·2.40.3에서 각각 135/135 PASS, 실패·skip 0 |
| 완료 | frontend 6/6 PASS 및 build PASS, Python 3.8 stdlib 양쪽 phase 검사 PASS, Python 3.12 검증 이미지 비루트 build/smoke PASS |
| 미완료 | 현재 NAS의 실시간 상태 조회, 실제 NAS 백업의 복구 검증, 실제 NAS DB/네트워크/볼륨/브라우저 로그인 검증 |
| 미완료 | NAS 반입용 backend/frontend 최종 이미지 build·불변 ID 확정 및 코드/이미지 manifest 승인. 이번에 build·실행 검사한 것은 로컬 검증 이미지다 |
| 승인 필요 | 검증 이미지 반입/임시 NAS 검증 컨테이너 실행, NAS 백업·DB 역할 생성·0014 적용·초기 비밀번호 설정 |
| 승인 필요 | 이후 신규 SCM 전용 서비스 기동. DB 변경 승인과 실제 서비스 실행 승인은 별개 |

로컬 DB는 54개 public 테이블을 구성한 **합성 fixture**다. users·mapping·grants와 50개 대표 업무 테이블의 테스트 레코드를 사용했다. 이 결과를 실제 NAS의 54개 업무 테이블 전체 또는 실데이터 복구 완료로 해석하지 않는다. 운영 데이터 보존 확정에는 승인된 실제 `new_scm_dev` 백업의 별도 격리 복구 검증이 필요하다.

최종 검사는 135개씩 두 번 모두 통과했고 환경 누락 SKIP은 없었다. 테스트 클라이언트에서 비차단 httpx 사용 중단 예정 경고가 있었으며 기능 실패는 없었다. 변경 범위는 기존 4-2H 미커밋 파일을 포함한 `new-scm` 내부 55개 파일이며 민감정보 패턴/Git 대상 env·백업/공백 검사를 통과했다. 소스 HEAD는 `206e22cc8c1b248af446c062686234a1bd1ff0b8` 그대로다. 이 HEAD가 미커밋 4-2I 변경을 포함한다는 뜻은 아니며, 실제 반입 전에 변경분과 artifact를 확정·검토해야 한다. Git Commit·Push도 별도 승인 사항이다.

## 중단 시점과 이어서 완료한 변경

중단 전에는 phase/PENDING 분기, 인증 스키마 카탈로그 검사, 0014 역할 검사 보강, 적용·실패·복구 테스트 코드가 작성돼 있었다. 실제 PostgreSQL 실행, 새 분기의 회귀, 최종 문서는 미완료였다. 기존 변경을 reset/stash/덮어쓰지 않고 다음 부분을 마무리했다.

| 파일 | 4-2I 변경 |
|---|---|
| `deploy/preflight.py` | pre/post phase, writer 미준비 허용 범위, PENDING protocol/exit, 보호 상태 변경 우선 FAIL, 안전한 CLI 오류 |
| `deploy/protected_state.py` | check-config에 동일 phase 전달, 고정 CLI 오류 유지 |
| `backend/app/db/auth_policy.py` | 컬럼 형식/NOT NULL/PK/FK/삭제·갱신 동작/인덱스/CHECK 검사, DB CREATE 권한 거부 |
| `backend/alembic/versions/20261028_0014_standalone_auth.py` | 로그인 가능·NOINHERIT·비특권·membership 없는 역할 및 CREATE 권한 사전 차단 |
| `backend/alembic/env.py` | URL query를 통한 DB/role/service 대상 우회 차단, psycopg 드라이버 고정, 백업 소유자·600·symlink 방지 |
| `backend/tests/migration_fixtures.py` | 검증된 로컬 컨테이너만 백업/새 DB 복구, 데이터 digest·DDL·ACL·시퀀스 비교 |
| `backend/tests/test_auth_postgresql.py` | 실제 Alembic 환경 실행, schema drift/제약조건/RO/PENDING/백업 복구/실패 및 재시도/차단된 downgrade 검증 |
| `backend/tests/test_local_auth.py` | migration URL 및 백업 보호 회귀 추가 |
| `deploy/test_migration_phases.py` | 신규 phase/고정 오류/PENDING 우회 방지/Compose 실검사 12개 |
| `deploy/run_tests.py` | 격리 fixture 컨테이너 지정 옵션 |
| `deploy/run_local_postgres_tests.py` | WSL 로컬 전용, network=none/미게시 포트/임시 DB 자동 생성·검사·정리 |
| README 및 4-2H 준비서 | 최신 4-2I 절차 안내 추가; 기존 기록 유지 |

## 적용 전·후 검증 규칙

| 검사 | `--phase pre-migration` | `--phase post-migration` (기본값) |
|---|---|---|
| 설정 | 기존 RO URL 필수, auth URL은 비어 있어도 허용; 값이 있으면 엄격 검사 | RO/auth 별도 역할 URL 필수, 같은 host/port/DB |
| DB | new_scm_dev / new_scm_ro / transaction_read_only=on | 동일 RO 검사 후 auth 연결도 read-only transaction |
| public | 54개, Alembic 0013, 과도한 RO 쓰기·소유·승격 권한 없음 | 54개, Alembic 0014, 동일 RO 권한 검사 |
| auth schema | 존재하지 않아야 함. 부분 생성/버전 불일치는 FAIL | 3개 테이블의 실제 구조·제약·인덱스·권한 필수 |
| auth 계정 연결 | 수행하지 않음 | new_scm_auth, 비특권·무membership·비소유·schema/DB CREATE 없음 |
| 준비 미완료 | `PENDING auth_migration_required` | 유효한 관리자 인증 정보가 없으면 `PENDING standalone_admin_setup_required` |
| 위험/구조 오류 | FAIL, 변경하지 않음 | FAIL, 변경하지 않음 |

- 전체 DB 검사 종료 코드는 PASS=0, FAIL=1, PENDING=2다. PENDING은 기동 허가가 아니다.
- `--config-only`의 0은 **설정 검사만 통과**라는 뜻이다. DB에 접속하지 않고 `PENDING database_runtime_checks_not_run`을 출력한다.
- 보호 포트/기존 PostgreSQL 상태가 검사 도중 변하면 예상된 PENDING보다 FAIL을 우선한다.
- worker 내부 PENDING은 예약 종료 코드 23 + 등록된 고정 코드만 허용한다. 기존 4-2G Docker/Python/DB 실패 분류와 4-2H 기본 post/기존 worker payload 동작을 유지했다.
- 일반 사용자 소유·600·비 symlink env 검사, sudo -n Docker allowlist, 메모리 제한, 비루트/read-only/cap-drop/no-new-privileges/tmpfs, CPU/PID 감지와 고정 경고는 유지한다.
- 이전 검증 이미지는 재사용하지 않는다. 동일 소스로 다시 build/비루트 smoke 검사를 거쳐 승인된 불변 이미지로 반입한다. 스크립트 hash가 다르면 FAIL이다.
- 과거 SSO 환경파일은 독립 설정으로 호환되지 않는다. 기존 `.env`는 보존하고 별도 `.env.standalone`을 준비한다. legacy handoff/identity 값이 있으면 거부한다.

## 독립 인증 및 관리자 설정

런타임은 자산관리 인증 서버·SSO·handoff를 호출하지 않는다. 보존한 mapping/0013/identity repository는 과거 데이터 보존 테스트용이며 로그인 경로에서 사용하지 않는다. 기존 자산관리 시스템을 중지해서 독립성을 시험하지 않았다. 로컬에서 외부 HTTP 클라이언트 생성을 차단한 상태로 실제 DB 로그인·로그아웃이 통과했다.

- Argon2id 64 MiB/time_cost=3/parallelism=1, 새 비밀번호 12–256자, 해시 계산 동시 2개.
- 난수 세션은 DB에 digest만 저장, 절대 만료 30분, 로그아웃/초기화/차단 시 서버 세션 무효화.
- HttpOnly, SameSite=Strict, Path=/api/v1, production Secure. 상태 변경은 정확한 Origin 필수. LAN HTTP·임의 forwarded identity·기본 Bearer JWT를 허용하지 않는다.
- 고정 15분 구간 계정 5회/peer 50회 제한은 DB atomic upsert로 여러 연결에 적용한다. 프록시 뒤에서는 peer 제한이 공유되며 X-Forwarded-For를 임의 신뢰하지 않는다.
- 관리자 API는 active + system.access + account_type=admin + admin.manage가 모두 필요하다. 일반 계정·위조 identity·미인증 요청의 차단을 확인했다.
- 기본 암호나 자동 운영 관리자 생성은 없다. 기존 public.users.password_hash를 추정/변환/갱신하지 않는다. 일반 웹 관리 화면은 기존 승인 사용자에 대한 전용 비밀번호 설정/로그인 차단만 지원한다. 신규 업무 사용자 생성/승격은 별도 승인 프로비저닝 범위다.

**개발 fixture:** `run_local_postgres_tests.py`가 빈 로컬 PostgreSQL에 admin-local/employee-local 및 승인 테스트 grant를 만들고 합성 비밀번호를 해시한다. 네트워크와 포트를 공개하지 않으며 검사 후 DB를 제거한다. 이 fixture와 테스트 비밀번호를 NAS에 적용하지 않는다.

**운영 초기 설정:** 승인된 기존 SCM user ID를 조회로 선택한다. active admin이며 승인된 system.access/admin.manage가 이미 있어야 한다. 없으면 중단하고 계정/권한 승인을 별도로 준비한다. 승인된 Python 3.12 운영자 PC의 별도 600 `.env.bootstrap`(동일 SSH tunnel 대상의 두 DB URL, URL 인코딩된 unquoted 값)로 아래 명령을 사용한다. 비밀번호는 TTY에 숨김 입력 2회이며 인자·로그·보고서에 넣지 않는다. NAS Python을 변경하거나 Python 전체를 sudo로 실행하지 않는다.

```sh
# DB 쓰기 승인 및 0014 완료 이후에만
python deploy/manage_auth.py --env-file .env.bootstrap --user-id <승인한SCM사용자ID> --initial-admin
```

## DB 보존·권한·복구 검증

0014는 `scm_auth.credentials`, `sessions`, `login_limits`를 새로 만들고 필요한 SELECT/USAGE/DML만 부여한다. 기존 public 테이블 구조·사용자·mapping·업무 데이터는 변경하지 않는다. Alembic 버전 행과 **신규 auth 역할에 대한** public SELECT/USAGE 추가가 의도된 차이다. 기존 역할의 ACL과 데이터는 비교해 보존을 확인했다.

- credentials.user_id → public.users.id FK는 RESTRICT, 세션 → credentials FK는 CASCADE; NOT NULL/PK/복합 PK/Argon2id prefix CHECK/세션 만료 CHECK/조회·만료 인덱스를 카탈로그와 실패 INSERT로 검증했다.
- new_scm_auth는 users의 승인된 5개 컬럼·grants·Alembic SELECT와 인증 3개 테이블 DML만 사용한다. 기존 비밀번호 SELECT, public 쓰기, 소유권, 승격, schema/DB CREATE는 차단한다. new_scm_ro의 업무·인증 쓰기 실패도 실제 테스트했다.
- 실제 Alembic command/env로 0014 적용 및 버전 갱신을 실행했다. 연결 factory만 이미 격리된 Unix socket으로 바꾸었고 URL/backup/DB identity guard는 실행했다. 별도로 DDL 중간 오류를 주입해 원상 롤백→같은 0013 상태에서 재시도 성공을 확인했다.
- pg_dump custom 백업을 적용 전·후 각각 만들고, 원본을 덮어쓰지 않는 새 격리 DB에 `pg_restore --exit-on-error --single-transaction`으로 복구했다. 모든 fixture 테이블의 row count/digest, 컬럼, 제약, 인덱스, ACL, 시퀀스를 비교했다. pg_restore가 재파싱하는 기존 grant enum의 동일 의미 varchar/text-array cast만 제한적으로 정규화했고 허용 값/컬럼/연산자는 유지했다.
- schema drift, FK/expiry/hash/중복 오류, 부적절한 auth 역할의 migration 차단, 자동 downgrade 거부를 확인했다. 백업 내용은 테스트 메모리/임시 600 파일에만 두고 출력/Git 포함하지 않았다.
- 실제 NAS 백업에는 비밀번호 해시/세션이 포함될 수 있으므로 700 디렉터리·소유자 600·Git 제외·접근 통제가 필수다. 백업의 실제 DB 출처와 PostgreSQL 서버/도구 major 호환성은 승인 단계에서 확인한다. PGDMP 헤더 확인만으로 복구 가능성이 증명되지는 않는다.

복구 명령의 의미는 [PostgreSQL pg_restore 공식 문서](https://www.postgresql.org/docs/16/app-pgrestore.html)를 따른다. 이번 복구 실험은 PostgreSQL 16의 합성 fixture이며 실제 NAS 백업 복구 증빙을 대체하지 않는다.

## NAS 적용 명령과 실행 순서

모든 경로는 `new-scm` 기준이다. 아래 1단계와 2단계 이후를 구분하며 이 작업에서는 NAS 명령을 실행하지 않았다.

### 1. 변경 없는 설정 확인 — 서비스/DB 변경 없음

별도 `.env.standalone`은 소유자 계정/600으로 운영자가 준비하고 기존 `.env`를 덮어쓰지 않는다. auth URL은 승인 전 비워둘 수 있다. 이미 반입된 승인 이미지 ID 2개가 든 `.nas-test-images.env`도 600이어야 한다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --phase pre-migration --config-only
PYTHONDONTWRITEBYTECODE=1 python3 deploy/protected_state.py check-config --env-file .env.standalone --phase pre-migration
```

### 2. 임시 NAS 검증 컨테이너 실행 승인 후 — DB 조회만

NAS Python 3.8은 config-only에 사용한다. 전체 DB 검사는 승인된 Python 3.12 검증 이미지가 필요하다. 이 명령도 임시 컨테이너를 시작하므로 **이번 단계에서는 실행 금지**다. sudo 인증은 사용자가 같은 터미널에서 입력하며 검증 스크립트 자체는 일반 사용자로 실행한다.

```sh
sudo -v
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --phase pre-migration --docker-sudo --isolated-image new-scm-preflight:4-2i
```

기대 결과는 기존 RO DB 검사 PASS + `PENDING auth_migration_required`, 종료 2다. 이 상태를 없애려고 DB를 자동 수정하지 않는다. FAIL이면 고정 코드만 보고하고 중단한다.

### 3. 별도 DB 변경 승인 후 — 백업/역할/0014/초기 관리자

1. new_scm_dev 전용 백업을 승인된 읽기/백업 계정으로 확보하고 별도 격리 DB에 복구해 54개 public 테이블·데이터·기존 ACL·0013을 비교한다. asset_manager_prod/공유 컨테이너 복구는 대상이 아니다.
2. DBA가 정확한 DB와 대상 역할을 확인한 대화형 psql에서 아래 역할 스크립트를 실행한다. 이미 역할이 있으면 자동 덮어쓰지 말고 중단/검토한다. `\password` 프롬프트에만 비밀번호를 입력한다.
3. 전용 migration 역할(RO/auth runtime 계정 금지), 안전하게 주입한 SCM_MIGRATION_DATABASE_URL/ROLE/BACKUP_PATH를 사용한다. 허용 대상은 psycopg / 127.0.0.1:5432 / new_scm_dev이며 URL query는 금지다. 운영자 PC의 승인된 SSH DB tunnel로 연결할 수 있다. 실제 URL/비밀번호를 명령행에 넣지 않는다.
4. 0014 적용 후 승인한 기존 관리자에 대해 위 manage_auth 명령을 실행한다.

```sh
# 승인된 new_scm_dev psql 세션 내부, 비밀번호는 프롬프트 입력
\i deploy/standalone_auth_role.sql
# 환경변수/백업/대상/tunnel을 안전하게 준비한 Python 3.12 운영자 터미널
python -m alembic -c backend/alembic.ini upgrade 20261028_0014
```

DDL은 새 인증 테이블을 만들지만 FK가 기존 users를 참조하므로 잠금/공유 PostgreSQL 자원 영향이 0은 아니다. 승인된 유지보수 시간, 기존 writer 중지 여부와 보존 조건, 타임아웃/오류 중단 기준을 먼저 확정한다. 기존 PostgreSQL 컨테이너·운영 서비스를 재시작하지 않는다.

### 4. 적용 후 엄격 검증 — 신규 SCM 서비스 기동 전

auth URL을 별도 파일에 준비한 뒤 일반 사용자로 실행한다. 관리자 미설정이면 PENDING으로 멈추고 임의 사용자/암호를 생성하지 않는다. 이미지 실행에 대한 기존 승인이 있어야 한다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --phase post-migration --config-only
sudo -v
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --phase post-migration --docker-sudo --isolated-image new-scm-preflight:4-2i
PYTHONDONTWRITEBYTECODE=1 python3 deploy/protected_state.py check-config --env-file .env.standalone --phase post-migration
PYTHONDONTWRITEBYTECODE=1 python3 deploy/protected_state.py capture --env-file .env.standalone --docker-sudo --file runtime/4-2h/4-2i-before-start.json
```

DB/권한/초기 관리자 검사가 모두 PASS여도 실제 실행 승인을 의미하지 않는다. capture는 새 파일만 만들며 기존 baseline을 덮어쓰지 않는다.

### 5. 별도 서비스 실행 승인 후

[4-2H 실행 준비서](SCM_NAS_4_2H_READINESS.md)의 전용 `new-scm-4-2h` 프로젝트와 동일 불변 이미지 manifest를 사용한다. 보호 compare 명령에는 반드시 같은 `--file runtime/4-2h/4-2i-before-start.json`을 사용한다. 운영 Compose와 병합하지 않는다.

1. baseline compare → relay만 기동 → compare.
2. backend 기동 → socket/database/auth/health 고정 probe → compare.
3. frontend 기동 → 127.0.0.1:8011 JSON health/직접 로그인/일반 사용자 403/로그아웃 확인 → compare.
4. 임계 자원/기존 서비스 상태/PG 상태 변화 또는 probe FAIL이면 신규 프로젝트만 즉시 stop. 자동 재기동·권한 확대·재마이그레이션으로 우회하지 않는다.

사용자 PC의 SSH tunnel은 `ssh -p 9680 -N -L 8011:127.0.0.1:8011 yeong00o@192.168.222.210` 후 정확히 `http://127.0.0.1:8011`로 접속한다. LAN HTTP나 자산관리 origin을 인증 경로로 사용하지 않는다. 운영 HTTPS 주소/종료 프록시는 별도 승인 설정이며 기존 80/8080/3010/8010은 변경하지 않는다.

## 실행 전 위험과 보호·롤백 조건

- **Docker Engine 28 미만:** localhost 게시가 같은 L2에서 노출될 수 있다. Compose 버전과 별개다. 기존 네트워크 차단 증빙이 없거나 버전이 불명확하면 기동 NO-GO다. 이번 작업에서 방화벽/daemon/권한/커널을 바꾸지 않는다. [Docker 공식 포트 게시 설명](https://docs.docker.com/engine/network/port-publishing/)
- **CPU/PID:** NAS 미지원 감지/고정 경고를 유지한다. 테스트 프로파일은 해당 옵션이 없고 메모리 상한은 relay64/backend256/frontend128 MiB다. 완전한 자원 격리는 아니며 CPU·PID·DB 연결 부하, Argon2 최대 동시 해시 메모리, relay 연결 수의 영향을 승인 전에 평가한다.
- **파일/네트워크:** UID10001 volume copy-up 및 700 socket, backend RO mount와 실제 relay 통신은 NAS 현장 검증이 남는다. 소켓 chmod/사용자 그룹/Docker 권한 변경을 우회책으로 사용하지 않는다.
- **인증/로그:** HttpOnly/SameSite/Secure/정확한 Origin을 유지한다. nginx peer 로그인 제한이 공유되므로 대규모 운영에는 승인된 trusted proxy/용량 정책이 필요하다. 임시 프로파일은 log-driver=none이라 운영 감사 로그 보관 정책도 별도 확정해야 한다.
- **Migration 실패:** PostgreSQL DDL 트랜잭션을 롤백하고 0013/schema 부재/기존 데이터·ACL을 조회로 재확인한다. 부분 상태가 남으면 중단한다. 수동 stamp/반복 migration/기존 컨테이너 재시작을 하지 않는다.
- **Migration 성공 후 코드 문제:** 신규 SCM만 stop하고 승인된 이전 이미지/설정을 복원한다. 인증 schema/hash/session은 보존하며 0014 downgrade는 차단된다. 과거 handoff 운영으로 자동 복귀하지 않는다.
- **DB 복구 필요:** 먼저 승인된 백업을 별도 DB에 복구·비교하고 데이터 손실 범위와 대상 전환을 별도 승인받는다. 운영 new_scm_dev 덮어쓰기 복구는 이번 절차에서 자동 실행하지 않는다. asset_manager_prod·기존 SCM/CMS·공유 PostgreSQL 복구/재시작은 금지다.
- **정리:** 새 프로젝트 stop/down만 허용 범위로 준비한다. `down -v`, --remove-orphans, prune, 기존 프로젝트/전체 컨테이너 stop/rm은 금지다.

## 로컬 재현

Python 3.12 가상환경 및 requirements를 사용한다. 다음 도구는 **WSL/Ubuntu 로컬 Docker**만 허용하고 NAS에서는 실행을 거부한다. 기존 캐시 PostgreSQL 16 이미지를 불변 ID로 해석하며 pull/sudo/외부 포트를 사용하지 않는다. 개발 fixture를 임시 메모리 저장소에 만들고 매 실행 후 컨테이너와 socket을 정리한다.

```sh
python -B deploy/run_local_postgres_tests.py --compose-executable <Compose실행파일> --verifier-image sha256:<검증이미지ID>
cd frontend
npm test
npm run build
```

Compose 실행 파일을 2.20.1과 2.40.3으로 각각 지정해 전체 검사를 수행했다. 2.20.1은 공식 배포 SHA-256을 확인했다. 일반 `deploy/run_tests.py`만 실행하면 환경 없는 검사가 SKIP될 수 있으므로 그 결과를 전체 검증 PASS로 표시하지 않는다. 다음 단계 진입에는 실제 NAS 백업 복구 증빙, 올바른 이미지 반입, 최소 권한/관리자 준비, 네트워크 비공개/자원/운영 로그 검토와 별도 실행 승인이 모두 필요하다.
