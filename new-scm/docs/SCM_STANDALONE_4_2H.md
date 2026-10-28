# 4-2H SCM 독립 운영 전환

최신 적용 전·후 검증과 복구 결과는 [4-2I 보고서](SCM_NAS_4_2I_VERIFICATION.md)를 따릅니다. 아래 기존 명령에서 phase를 생략하면 post-migration 검사이며, 아직 0013인 NAS는 `--phase pre-migration`으로 조회합니다.

## 변경 결과와 범위

개발 변경은 모두 `new-scm` 내부입니다. NAS/운영 DB에는 접속하거나 변경하지 않았고 기존 컨테이너·서비스·포트·소스도 수정하지 않았습니다. 커밋·Push는 하지 않았습니다.

| 대상 | 변경 | 보존 |
|---|---|---|
| backend/core/auth_routes.py, local_auth.py, auth.py | 직접 로그인·로그아웃·권한 검사·관리자 인증 계정 설정 | 미인증 차단, 메뉴/작업 권한 별도 검사 |
| backend/db/local_auth.py, auth_policy.py | 인증 전용 DB 연결과 최소 권한 조회 검사 | 업무 조회 `new_scm_ro` 및 Unix relay |
| backend/alembic/versions/20261028_0014_standalone_auth.py | 별도 `scm_auth` 스키마·3개 테이블 | 기존 public 54개 테이블, 사용자·기존 비밀번호·매핑 |
| frontend/src/pages/LoginPage.jsx, AuthContext, authService | SCM 주소에서 직접 로그인·로그아웃·세션 만료 확인 | 기존 메뉴·업무 화면·서버 권한 기반 접근 제어 |
| frontend/src/pages/settings/AccountManagement.jsx | 실제 기존 계정의 비밀번호 설정/로그인 차단, 세션 폐기 | public 사용자·역할·업무 데이터는 수정하지 않음 |
| deploy/preflight.py, Dockerfile.preflight, protected_state.py, nas_check.py | 독립 인증 스키마·계정·초기 관리자 검사, 과거 인증 API 호출 제거 | Python 3.8 설정 검사 / 3.12 격리 검사, sudo 제한, 600 소유권, CPU/PID 대응 |
| deploy/compose*.yaml | 자산관리 `extra_hosts`·identity URL 주입 제거 | loopback 8011, 내부 API 8012, 전용 Unix volume |
| run_backend.ps1, .env*.example | 별도 개발 파일과 reload, 독립 배포 설정 예시 | NAS 실제 `.env` 미수정 |

삭제한 런타임은 `handoff.py`, 메모리 `scm_session.py`, `/auth/handoff` 라우트입니다. 자산관리 소스를 불러오던 계약 테스트도 제거하고 독립 인증 테스트로 대체했습니다. `db/identity.py`와 revision 0013은 기존 매핑 데이터 보존/회귀 검사에만 남아 있으며 로그인 경로에서 호출하지 않습니다. `SCM_HANDOFF_KEY`, `SCM_HANDOFF_ORIGIN`, `SCM_IDENTITY_BASE_URL`은 현재 설정에서 사용하지 않습니다. 과거 `.env`나 Git 이력의 실제 키를 읽거나 출력하지 않습니다.

## 인증 동작

- `POST /api/v1/auth/login`: SCM username/password, Argon2id(64 MiB, time_cost=3, parallelism=1), 12–256자 새 비밀번호. 기존 비밀번호를 추측·재사용·자동 변환하지 않습니다.
- 암호 검증은 동시 2개로 제한합니다. 슬롯이 차면 고정 `auth_busy` 503으로 중단하며 NAS 메모리 부족 시 제한을 자동 완화하지 않습니다.
- 48바이트 난수 기반 불투명 세션, DB에는 SHA-256 digest만 저장. 30분 절대 만료, 재로그인 시 브라우저의 이전 세션 폐기. DB 재연결/서버 재시작 후에도 만료 전 세션을 조회합니다.
- `GET /auth/me`: 매 요청마다 활성 사용자·인증 enabled·현재 SCM 권한을 다시 확인합니다. `system.access`가 없으면 403, 유효한 세션이 없으면 401. 기본 Bearer 검증기는 비활성으로 외부 JWT/identity 헤더를 신뢰하지 않습니다.
- `POST /auth/logout`: 서버 세션 삭제 후 쿠키 삭제. DB 오류 시 성공으로 표시하지 않습니다.
- 쿠키는 HttpOnly, SameSite=Strict, Path=/api/v1, production에서 Secure. 토큰/비밀번호를 LocalStorage나 API 응답에 저장하지 않습니다. 인증 응답은 오류를 포함해 no-store입니다.
- 로그인·로그아웃·관리자 변경은 정확한 `SCM_FRONTEND_ORIGIN`의 Origin이 필수입니다. 누락/null/다른 origin과 LAN HTTP를 거부합니다.
- 고정 15분 구간에서 계정당 5회, 연결 peer당 50회까지 시도 가능. 성공 시에도 카운터를 초기화하지 않으며 PostgreSQL atomic upsert로 여러 프로세스/재시작/동시 시도에 적용합니다. 차단 peer는 새 계정 bucket을 만들지 않습니다.
- 알려지지 않은 계정·비밀번호 오류·차단 계정은 동일한 401 `invalid_credentials`. 모르는 계정도 dummy Argon2 검증을 합니다. 429에는 Retry-After=900, 예상치 못한 오류는 503 `auth_unavailable`만 반환합니다.
- 로그는 `auth_login_succeeded/rejected/throttled`, `auth_logout_succeeded`, `auth_credentials_changed`, `auth_storage_unavailable` 등 고정 이벤트만 기록합니다. 비밀번호·해시·토큰·DB URL·username·IP를 보안 이벤트에 기록하지 않습니다. 요청 로그도 경로 템플릿만 사용합니다.
- 관리자 API는 account_type=admin **및** system.access **및** admin.manage가 모두 필요합니다. 일반 사용자에게 admin.manage 문자열이 잘못 있어도 관리자 API는 차단됩니다. 비밀번호 재설정/비활성화는 해당 사용자의 모든 세션을 폐기합니다. 자신의 인증 정보는 브라우저에서 변경하지 않고 승인된 운영자 CLI를 사용합니다.

새 사용자 생성·승격·메뉴/업무 권한 변경은 이번 웹 인증 API에 넣지 않았습니다. 기존 사용자와 승인된 `scm_user_grants`를 재사용하며, 신규 사용자/권한 추가가 필요하면 별도의 승인된 프로비저닝 절차로 준비해야 합니다. 자동 관리자·기본 비밀번호·자동 전체 메뉴 권한 부여는 없습니다.

## DB 변경 계획 — NAS에서는 미실행

리비전은 `20261027_0013 → 20261028_0014`입니다. 새 테이블은 `scm_auth.credentials`, `scm_auth.sessions`, `scm_auth.login_limits`뿐입니다. public 테이블 수는 54개로 유지되며 기존 `users.password_hash`, 매핑, 업무 데이터는 갱신하지 않습니다. credentials는 기존 user_id FK를 사용합니다. Alembic 버전 행은 승인된 migration 시에만 갱신됩니다.

`new_scm_auth`는 NOINHERIT/NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS 전용 로그인 역할입니다. 0014는 역할이 안전하게 사전 생성되어 있지 않으면 중단합니다.

| 역할 | 허용 | 금지 |
|---|---|---|
| new_scm_ro | 기존 업무 SELECT, 읽기 전용 transaction | 업무/인증 쓰기 |
| new_scm_auth | users의 id/username/name/account_type/status SELECT, SCM grants·Alembic 버전 SELECT, 인증 3개 테이블 SELECT/INSERT/UPDATE/DELETE | 기존 비밀번호 SELECT, public 쓰기, schema CREATE, role 승격, 테이블 소유권 |
| 승인된 migration 역할 | 백업 확인 후 0014 DDL/명시적 GRANT | 앱 컨테이너에 자격증명 제공 |

사전 검증은 두 계정 모두 **읽기 전용 transaction**으로 연결합니다. writer의 쓰기 가능성은 has_table_privilege 등 카탈로그 조회로 검사하며 실제 테스트 INSERT/UPDATE를 NAS에서 수행하지 않습니다. 역할 membership/상속/소유권/과도한 업무 쓰기/기존 비밀번호 읽기 권한도 거부합니다.

승인 후 순서:

1. 신규 서비스 중지 상태에서 `new_scm_dev` 전용 custom-format 백업을 승인된 계정으로 확보합니다. 파일은 `runtime/backups/` 내부 600, 디렉터리 700, Git 제외. 임시 별도 DB에서 복구 검증하고 기존 54개 public 테이블·버전·사용자/매핑 데이터를 기록합니다. 실제 비밀번호/해시는 보고서에 넣지 않습니다.
2. DBA가 정확한 DB 접속을 확인하고 `deploy/standalone_auth_role.sql`을 대화형 psql에서 실행합니다. 비밀번호는 `\password` 입력창에만 입력합니다. 역할이 이미 있으면 자동 덮어쓰지 않고 중단/검토합니다. 다른 DB에 연결하면 이 스크립트가 거부합니다.
3. Python 3.12 운영자 환경에 migration 계정과 `SCM_MIGRATION_ROLE`, `SCM_MIGRATION_BACKUP_PATH`를 안전하게 설정합니다. URL은 `SCM_MIGRATION_DATABASE_URL`, 대상은 new_scm_dev / 127.0.0.1:5432만 허용합니다. NAS의 15432에는 운영자 PC의 승인된 SSH 터널로 연결할 수 있습니다. 실제 URL/암호를 명령행·로그·대화에 출력하지 않습니다.
4. `new-scm`에서 `python -m alembic -c backend/alembic.ini upgrade 20261028_0014`. 앱 시작 시 자동 migration은 없습니다. 0014는 실패하면 트랜잭션 롤백됩니다.
5. 기존 활성 SCM 관리자와 승인된 system.access/admin.manage를 조회로 확인합니다. 특정 id를 기본 관리자로 가정하지 않습니다. 해당 조건을 갖춘 사용자가 없다면 여기서 중단하고 별도의 계정/권한 승인을 준비합니다.
6. Python 3.12 운영자 터미널에서 `python deploy/manage_auth.py --env-file .env.bootstrap --user-id <승인된SCM사용자ID> --initial-admin`. 별도 bootstrap 파일은 일반 사용자 소유·600이며 두 URL을 같은 승인된 tunnel/DB로 지정합니다. 비밀번호는 두 번 숨김 입력하고 생성/출력하지 않습니다. NAS Python 업그레이드나 sudo Python은 필요하지 않습니다. 비대화형 입력은 거부합니다.
7. 검증 PASS 후에도 실제 SCM 서비스 기동은 별도 승인이 필요합니다.

백업·migration·역할/비밀번호 설정은 **실제 NAS DB 변경 승인 후** 수행할 절차이며 이번 개발에서 실행하지 않았습니다.

## 개발과 접속 주소

개발 `.env.development`는 localhost의 별도 테스트 DB/계정만 사용하고 `SCM_FRONTEND_ORIGIN=http://127.0.0.1:5174`로 지정합니다. 개발 5174는 배포 preflight에서 의도적으로 거부합니다. NAS 설정 파일은 새 `.env.standalone`을 수동으로 준비하고 기존 `.env`는 그대로 보존합니다. 예시는 `.env.example`이며 두 DB URL의 host/port는 같아야 합니다.

NAS 로컬 검증은 `SCM_ENV=development`, `SCM_FRONTEND_ORIGIN=http://127.0.0.1:8011`, 상대 API `/api/v1`입니다. 사용자 PC에서 `ssh -p 9680 -N -L 8011:127.0.0.1:8011 yeong00o@192.168.222.210` 터널 후 브라우저의 정확한 127.0.0.1 주소로 접속합니다. localhost/127.0.0.1을 혼용하지 마세요. NAS LAN IP HTTP 접속은 허용하지 않습니다.

운영 전환 시에는 승인된 SCM 전용 HTTPS 주소 한 개를 frontend origin으로 지정하고 `SCM_ENV=production`으로 설정합니다. HTTPS 종료 프록시는 loopback 8011로 연결해야 하며 이번 작업에서 기존 80/8080/3010/8010 또는 프록시를 변경하지 않았습니다. 서로 다른 자산관리/SCM 호스트는 이제 인증에 관여하지 않습니다. SCM에 직접 로그인하므로 cross-site handoff와 SameSite=None 완화가 필요하지 않습니다.

Nginx 뒤에서는 실제 peer가 Nginx 주소로 보입니다. 임의 X-Forwarded-For를 신뢰하지 않으며 peer 50회 제한이 공유됩니다. 운영 대규모 동시 로그인에는 승인된 trusted proxy 정책/용량 검토가 추가로 필요합니다.

## NAS 최종 검증 명령 — 설정만 먼저

아래는 `new-scm` 디렉터리, **일반 사용자 yeong00o**에서 실행합니다. 새 `.env.standalone`은 기존 `.env`를 덮어쓰지 않고 소유자 600으로 별도 준비합니다. `SCM_HANDOFF_*`, `SCM_IDENTITY_BASE_URL`이 남은 파일은 사전 검증이 거부합니다.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --config-only
```

Python 3.8 표준 라이브러리로 Compose 2.20.1 이상 version/config --quiet/JSON 정책 검사를 실행하며 Docker daemon sudo가 필요하지 않습니다. 원문 Compose JSON은 출력하지 않습니다.

독립 인증 코드와 동일한 소스로 다시 빌드/반입한 **승인된 Python 3.12 검증 이미지**가 있고 DB 준비 승인이 완료된 후:

```sh
sudo -v
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --env-file .env.standalone --docker-sudo --isolated-image new-scm-preflight:standalone-4-2h
```

sudo 암호는 사용자가 터미널에 직접 입력합니다. Python은 일반 사용자로 실행하며 Docker에는 sudo -n만 제한적으로 사용합니다. 이미지가 없으면 pull/build하지 않고 중단합니다. 이미지와 호스트 스크립트 hash가 다르면 중단합니다. Docker socket·env 파일을 검증 컨테이너에 마운트하지 않고 두 URL만 stdin payload로 전달하며, Docker stderr/예외를 출력하지 않습니다.

예상 진단: 설정 PASS, CPU/PID 미지원 시 `WARN verifier_cpu_limit_unsupported`, `WARN verifier_pid_limit_unsupported`, `WARN verifier_resource_limits_incomplete`. 메모리 미지원/지원 여부 불명은 실패합니다. 독립 DB 준비 전에는 `FAIL alembic_revision_invalid` 또는 `standalone_admin_not_provisioned`가 정상적인 차단입니다. 권한 오류는 auth_schema_privileges_invalid/auth_role_* 등의 고정 코드입니다.

검증 이미지 자체의 준비 빌드는 로컬 개발 PC에서만 수행하며 실제 NAS 서비스 실행 명령과 분리합니다:

```sh
docker build -f deploy/Dockerfile.preflight -t new-scm-preflight:standalone-4-2h .
```

## 롤백과 남은 제약

- NAS 서비스 기동/배포·실제 브라우저 로그인·Unix 볼륨·프록시 통신은 별도 승인 후 검증해야 합니다. 코드/자동 테스트의 PASS를 NAS 현장 PASS로 표시하지 않습니다.
- `compose.nas-test.yaml`은 전용 테스트 프로젝트·불변 image ID·restart=no·메모리 제한이며 CPU/PID 미지원 NAS에 해당 제한을 강제로 넣지 않습니다. CPU/PID의 완전한 격리는 제공하지 못합니다. 상세 영향과 중지 명령은 별도 readiness 문서에 있습니다.
- 업무 API는 기존과 같이 다수 미구현/404이며 업무 화면 상당수는 샘플/메모리 데이터입니다. 인증 전환은 그 업무 기능의 CRUD 구현을 포함하지 않습니다.
- 실제 운영 보안 로그 보존/접근 통제/보관 기간은 승인 전에 결정해야 합니다. 임시 NAS 테스트 프로파일은 log-driver=none으로 로그를 영구 보관하지 않습니다. 기본 배포/개발은 고정 보안 이벤트를 기록합니다.
- DB 문제 시 기본 오류 코드만 표시하고 서비스 시작을 반복하지 않습니다. DB/asset-postgres 재시작, 권한 확대, socket chmod, NAS Python/커널/cgroup 변경을 해결책으로 사용하지 않습니다.
- 코드 롤백 시 신규 SCM 전용 컨테이너만 중지하고 이전 이미지/설정 manifest로 돌아갑니다. 인증 세션/해시가 든 schema는 보존합니다. 0014 downgrade는 고의로 거부하므로 자동 schema 삭제가 없습니다.
- public.alembic_version을 임의로 stamp하거나 자산관리 handoff로 자동 복귀하지 않습니다. DB 복구가 필요하면 승인된 new_scm_dev 전용 백업을 먼저 별도 DB에 복구·검증하고, 데이터 손실 범위/대상 전환을 별도 승인받습니다. asset_manager_prod 또는 공유 PostgreSQL 컨테이너를 복구/재시작하지 않습니다.

참고 기준: [Argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html), [OWASP 인증](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [OWASP 세션 관리](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).


## 로컬 검증 결과 — 2026-10-28

| 검사 | 결과 |
|---|---|
| 전체 backend/deploy 회귀 + 실제 임시 PostgreSQL + Compose 2.40.3 | 111/111 PASS, 실패/skip 0 |
| 동일 검사 + 공식 checksum 확인 Compose 2.20.1 | 111/111 PASS, 실패/skip 0 |
| frontend `npm test` | 6/6 PASS |
| frontend `npm run build` | PASS |
| Python 3.8 이미지의 stdlib-only 독립 설정 정책 검사 | PASS, network=none / 비루트 / read-only |
| Python 3.12 검증 이미지 build 및 UID10001 읽기·import·실행 smoke | PASS |
| 실제 임시 PostgreSQL에 0013→0014 적용 | PASS, public 54개 유지 / 기존 사용자·비밀번호 컬럼·매핑 보존 |
| 별도 writer 권한, RO 쓰기 차단, 기존 비밀번호 SELECT 차단 | PASS |
| 로그인/로그아웃/만료/즉시 권한 취소/비밀번호 초기 설정/관리자 분리/동시 실패 제한 | PASS |
| 외부 인증 HTTP 호출을 차단한 실제 DB 로그인 | PASS |
| 변경 범위·민감정보 패턴·Git 대상 env/DB 백업 제외·diff 공백 검사 | PASS (합성 테스트 자격증명 제외) |
| 실제 NAS DB/서비스·브라우저/Unix volume·기동/배포 | 미실행·미검증, 별도 승인 필요 |

PostgreSQL은 로컬 Ubuntu Docker의 network=none·host port 없음·임시 메모리 저장소 클러스터만 사용했고 테스트 컨테이너를 정리했습니다. NAS나 기존 PostgreSQL에는 테스트 데이터를 쓰지 않았습니다. 전체 검사는 Linux Python 3.12와 격리 DB에서 수행했으며, Windows의 환경 없는 단순 실행은 111개 중 90 PASS / 21 SKIP입니다. 이 SKIP을 NAS 검증 PASS로 간주하지 않습니다.

비밀번호 라이브러리는 신규 SCM 로컬 가상환경/분리 테스트 의존성에 두었습니다. 기존 프로젝트 의존성 파일 및 NAS 기본 Python은 변경하지 않았습니다. 소스 HEAD는 기존 커밋 그대로이며 커밋·Push는 수행하지 않았습니다.

### 변경 파일 목록 (앞선 미커밋 NAS 준비 파일 포함)

- `new-scm/.dockerignore`
- `new-scm/.env.example`
- `new-scm/.gitignore`
- `new-scm/README.md`
- `new-scm/backend/alembic/env.py`
- `new-scm/backend/app/core/auth.py`
- `new-scm/backend/app/core/config.py`
- `new-scm/backend/app/core/handoff.py` (삭제)
- `new-scm/backend/app/core/scm_session.py` (삭제)
- `new-scm/backend/app/main.py`
- `new-scm/backend/requirements.txt`
- `new-scm/backend/tests/test_deployment.py`
- `new-scm/backend/tests/test_handoff.py` (삭제)
- `new-scm/backend/tests/test_identity_contract.py` (삭제)
- `new-scm/backend/tests/test_identity_repository.py`
- `new-scm/deploy/Dockerfile.preflight`
- `new-scm/deploy/check_preflight_image.py`
- `new-scm/deploy/compose.yaml`
- `new-scm/deploy/preflight.py`
- `new-scm/deploy/test_preflight.py`
- `new-scm/frontend/package.json`
- `new-scm/frontend/src/App.jsx`
- `new-scm/frontend/src/constants/permissions.js`
- `new-scm/frontend/src/contexts/AuthContext.jsx`
- `new-scm/frontend/src/pages/settings/AccountManagement.jsx`
- `new-scm/frontend/src/services/authService.js`
- `new-scm/run_backend.ps1`
- `new-scm/.env.development.example`
- `new-scm/backend/alembic/versions/20261028_0014_standalone_auth.py`
- `new-scm/backend/app/core/auth_routes.py`
- `new-scm/backend/app/core/local_auth.py`
- `new-scm/backend/app/core/nas_check.py`
- `new-scm/backend/app/core/provision_auth.py`
- `new-scm/backend/app/db/auth_policy.py`
- `new-scm/backend/app/db/local_auth.py`
- `new-scm/backend/tests/test_auth_postgresql.py`
- `new-scm/backend/tests/test_local_auth.py`
- `new-scm/deploy/compose.nas-test.yaml`
- `new-scm/deploy/manage_auth.py`
- `new-scm/deploy/nas-test.images.env.example`
- `new-scm/deploy/protected_state.py`
- `new-scm/deploy/run_tests.py`
- `new-scm/deploy/standalone_auth_role.sql`
- `new-scm/deploy/test_nas_preparation.py`
- `new-scm/docs/SCM_NAS_4_2H_READINESS.md`
- `new-scm/docs/SCM_STANDALONE_4_2H.md`
- `new-scm/frontend/Dockerfile.nas-test`
- `new-scm/frontend/nginx.nas-test.conf`
- `new-scm/frontend/src/pages/LoginPage.jsx`
- `new-scm/frontend/src/pages/login.css`
- `new-scm/frontend/tests/auth.test.js`
