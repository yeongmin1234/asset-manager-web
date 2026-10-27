# 신규 SCM 연결 복구: NAS 확인 결과와 실행 절차

2026-10-27, NAS 공유 경로와 HTTP를 읽기 전용으로 확인했다. 이 문서는 현재 상태를 기록하고, 독립 SCM 준비 후 기존 자산관리 프론트엔드만 반영하는 순서를 정한다. 실행 중인 NAS 서비스에는 이 조사로 변경을 가하지 않았다.

## 확인된 상태

- NAS 공유 경로: `\\192.168.222.210\총무\서버\자산관리 프로젝트\asset-manager-web` 접근 가능.
- 기존 자산관리 `http://192.168.222.210:3010/`, `http://192.168.222.210:8010/health`, `/health/db`는 모두 HTTP 200. 기존 프론트엔드가 제공하는 JS/CSS도 HTTP 200이고, 제공 중인 JS는 NAS `frontend/dist/index.html`의 해시와 일치한다.
- NAS `frontend/.env`에는 `VITE_SCM_API_URL`, `VITE_SCM_FRONTEND_URL`이 없다. 제공 중인 번들에는 `SCM 연결 주소가 설정되지 않았습니다.` 오류 문구가 있다.
- NAS `new-scm/.env`, `new-scm/frontend/dist/index.html`, `new-scm/runtime/logs`는 없다. 조사한 NAS 주소의 8011·8012·5174 포트에는 외부 연결이 되지 않았다. Compose 설정의 8011은 기본값이 `127.0.0.1`에만 바인딩되므로, 외부 포트 검사만으로 NAS 내부 프로세스 부재를 단정할 수 없다. NAS 셸에서 `docker compose ps`, 포트 리스너와 루프백 HTTP를 확인해야 한다.
- 기존 NAS `backend/.env`, `deploy/.env`에 `SCM_HANDOFF_KEY`가 없다. 실행 프로세스에 별도로 주입되었는지는 확인하지 못했다.
- `new-scm/docs/SCM_AUTH_4_2E_FINAL_RESULT.md` 기준, 신규 SCM 사용자 매핑·권한 테이블 마이그레이션은 백업 실패로 보류되었고 실제 사용자 grant가 없다.
- 기존 자산관리의 실제 로그인·자산 CRUD와 SCM 버튼 클릭은 계정 세션이 없어 검증하지 못했다. 무인증 `/auth/me`는 401이며, 이는 인증 보호의 정상 반응만 확인한다.

## 독립 신규 SCM 배포 전 확인

NAS 셸 접근 권한이 있는 담당자가 아래 **읽기 전용** 명령의 결과를 확인한다. 현재 SMB 접근은 가능하지만 NAS SSH 22번은 연결되지 않았다.

```sh
cd '/volume6/총무/서버/자산관리 프로젝트/asset-manager-web/new-scm'
docker compose -f deploy/compose.yaml ps
ss -ltnp | grep -E ':(8011|8012|5174)[[:space:]]' || true
curl --max-time 3 -i http://127.0.0.1:8011/
curl --max-time 3 -i http://127.0.0.1:8011/api/v1/system/status
```

프로세스가 없다면 현재 Compose 설계에서 필요한 사전 조건을 먼저 갖춘다. 신규 전용 `.env`와 DB 계정, 새 로그·업로드 경로, Compose 사용 가능 여부, 이미지 빌드 용량을 확인한다. `8011`은 신규 프록시의 NAS 루프백 포트로만 사용하고 80·8080·3010·8010은 변경하지 않는다. Compose의 컨테이너 내부 `80`은 NAS 호스트 포트 80과 다르다. 새 컨테이너를 실행하기 전에 NAS 운영 서비스 영향(리소스 사용, 포트, 역방향 프록시·TLS 설정)을 별도로 보고한다.

신규 SCM 공개 주소는 운영 HTTPS 역방향 프록시의 실제 호스트·경로를 확인하고, 사용자 PC에서 프론트엔드와 `/api/v1/system/status`가 정상 응답할 때만 확정한다. 현재 저장소의 `127.0.0.1:8011`과 개발용 `5174`·`8012`는 사용자 PC의 운영 SCM 주소가 아니다. `VITE_SCM_API_URL`은 `/api/v1/auth/handoff`를 붙일 수 있는 확인된 HTTPS 원점, `VITE_SCM_FRONTEND_URL`은 확인된 HTTPS 신규 프론트엔드 주소로 설정한다. 두 값을 임의의 NAS IP나 미검증 포트로 채우지 않는다.

## 주소 확인 후에도 필요한 인증 조건

1. 기존 백엔드 런타임의 `SCM_HANDOFF_KEY`가 32자 이상으로 설정되었는지 안전하게 확인한다. 신규 백엔드에는 동일한 별도 키와 `SCM_IDENTITY_BASE_URL`, `SCM_HANDOFF_ORIGIN`, `SCM_FRONTEND_ORIGIN`이 필요하다. 기존 백엔드에 키가 없다면 **기존 백엔드 재시작 금지** 조건 아래에서는 실제 인계 완료가 불가능하다. 환경파일만 고쳐도 실행 중인 프로세스에는 반영되지 않는다.
2. 신규 SCM DB의 전체 백업 실패를 해결하고 복구 가능한 백업을 확인한 뒤, 승인된 절차로 신규 매핑·grant 테이블을 적용하고 실제 사용자 ID를 검증하여 권한을 부여한다. 기존 자산관리 DB는 변경하지 않는다.
3. 기존 프론트엔드 출처에서 신규 API로 `credentials: include` 요청이 가능해야 한다. 신규 API CORS, HTTPS, 쿠키 SameSite/secure, 실제 브라우저의 쿠키 저장과 후속 `/api/v1/auth/me`를 검증한다. 현재 신규 코드의 `SameSite=Lax` 쿠키는 서로 다른 사이트 간 fetch에서 문제가 될 수 있으므로 실브라우저 확인 없이 인계 성공으로 판정하지 않는다.
4. 신규 SCM 업무 화면·권한과 통합 로그아웃은 별도 검증 항목이다. 현재 기존 기록에서는 통합 로그아웃이 미완료다.

## 기존 프론트엔드만 안전하게 반영하는 절차

위 주소와 인증 조건을 충족한 뒤 운영 영향 범위를 보고하고 진행한다. 기존 `deploy/deploy.sh`와 `deploy/full_deploy.sh`는 백엔드 중지·시작 및 Alembic 실행을 포함하므로 사용하지 않는다.

1. 기존 프론트엔드와 백엔드의 HTTP 200, 제공 중인 JS/CSS 해시, `frontend/dist` 백업을 기록한다. 현재 정적 서버는 `frontend/dist`의 절대 경로에서 요청마다 파일을 읽으므로, 같은 경로에 새 파일을 반영하면 프론트엔드 프로세스를 재시작할 필요가 없다.
2. 확인된 HTTPS 주소만 NAS `frontend/.env`의 두 `VITE_SCM_*` 값으로 넣는다. 기존 `VITE_API_BASE_URL`을 보존한다. 비밀값은 Vite 환경변수에 넣지 않는다.
3. 새 빌드를 `frontend/dist` 밖의 별도 임시 디렉터리에 만든다. `frontend/package-lock.json`에 맞는 `npm ci`, SCM 미리보기 빌드, `vite build --outDir <임시 경로>`를 사용한다. 빌드 결과에서 두 확인 주소, 해시 JS/CSS 존재, 구형 내부 API 주소 부재를 점검한다.
4. 기존 `dist`를 유지한 채 새 해시 자산을 먼저 복사한다. 기존 자산은 즉시 삭제하지 않는다. 새 `index.html`은 임시 이름으로 복사하고 동일 파일시스템 안에서 원자적으로 이름을 바꾸어 적용한다. 그 외 필요한 정적 파일도 목록을 대조해 반영한다. 기존 정적 서버·백엔드 프로세스는 중지하거나 재시작하지 않는다.
5. 제공 중인 `index.html`과 JS/CSS HTTP 200 및 새 해시 일치를 검사한다. 이상이 있으면 백업한 `index.html`을 원자적으로 되돌린다. 롤백 가능한 기간에는 이전 해시 자산을 보존한다.
6. 기존 계정으로 로그인·자산관리 핵심 조회를 확인한 뒤 SCM 버튼을 클릭한다. 주소 오류가 사라졌는지, 인계 API와 신규 SCM 세션·화면이 정상인지, 브라우저 콘솔 오류가 없는지 확인한다. 기존 백엔드 `/health`, `/health/db`를 전후 비교한다.

현재는 신규 SCM 운영 HTTPS 주소와 인증 조건이 확인되지 않아 2단계 이후를 실행하지 않는다.
