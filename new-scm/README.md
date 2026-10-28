# 신규 SCM 독립 실행 기반 (3단계)

이 폴더는 기존 자산관리 backend/frontend와 분리된 신규 SCM 작업본입니다. 이번 단계의 API는 상태 확인 전용이며 업무 데이터 쓰기 API가 없습니다. 실제 NAS 배포는 수행하지 않았습니다.

## 구성

- backend: FastAPI + SQLAlchemy + psycopg. DB는 new_scm_dev만 허용하고 DB 점검은 읽기 전용 세션으로 실행합니다.
- frontend: SCM 미리보기 화면 84개 파일을 복사한 독립 Vite 앱. 기존 자산관리 API 서비스와 작업기록 브리지는 복사본에서 비활성화했습니다.
- deploy: 신규 서비스만 담은 Docker Compose와 Nginx 프록시 설정.
- runtime: 신규 SCM 전용 로그·업로드 경로. 업로드 API는 아직 없습니다.

## 로컬 실행

PowerShell 창 두 개에서 각각 실행합니다.

1. 이 폴더에서 ./run_backend.ps1
2. 이 폴더에서 ./run_frontend.ps1
3. 브라우저에서 http://127.0.0.1:5174/

백엔드는 127.0.0.1:8012, 프론트엔드는 127.0.0.1:5174에만 바인딩됩니다. 각 창에서 Ctrl+C로 중지합니다. 프론트엔드 패키지는 신규 폴더 안에 독립 복사되어 있습니다. 재설치 시에는 새 폴더 안에서만 npm ci를 실행하세요.

- GET http://127.0.0.1:8012/health: 서버만 확인하며 DB에 접속하지 않습니다.
- GET http://127.0.0.1:8012/api/v1/system/status: 프론트엔드 상태 표시용입니다.
- GET http://127.0.0.1:8012/api/v1/system/db-status: X-SCM-Diagnostics-Key 헤더가 필요합니다. DB가 설정되지 않은 현재 상태에서는 503입니다.

프론트엔드의 `VITE_SCM_API_BASE_URL`은 `/api/v1`로 고정 검증합니다. 설정은 `.env.example`에 기록되어 있으며, 브라우저 요청은 같은 출처의 프록시를 통해서만 전송됩니다. 임의의 외부 API 주소는 허용하지 않습니다.

기존 `.env`는 덮어쓰지 않습니다. `SCM_DATABASE_URL`은 `postgresql+psycopg` 드라이버와 `new_scm_ro` / `new_scm_dev`만 허용하며 URL query는 금지합니다. 비밀번호는 URL 인코딩하고 명령행이나 보고서에 넣지 마세요. 모든 DB 연결에 `default_transaction_read_only=on`과 statement timeout을 적용합니다.

## 배포 준비

NAS Python 3.8.15의 의존성 없는 설정 검사와 Docker 소켓을 노출하지 않는 선택적
Python 3.12 검증 환경은 [4-2G 사전 검증 안내](docs/SCM_PREFLIGHT_4_2G.md)를 따릅니다.
`python3 deploy/preflight.py --config-only`는 표준 라이브러리만 사용합니다.
DB/API 전체 검사는 Python 3.12 의존성 또는 별도 검증 이미지가 필요합니다.
Docker 데몬에 sudo가 필요한 NAS에서는 같은 터미널에서 `sudo -v`로 인증한 뒤 일반
사용자로 `--docker-sudo --isolated-image new-scm-preflight:4-2g` 옵션을 사용합니다.
Python 전체를 sudo로 실행하거나 `.env`의 소유권·600 권한을 바꾸지 않습니다.

Compose 2.20.1 호환 설정입니다. 프론트엔드·백엔드는 `scm_internal`에서 통신하고 NAS 공개 포트는 `127.0.0.1:8011`뿐입니다. 별도 `db-relay`만 host 네트워크를 사용해 기존 `127.0.0.1:15432`에 연결합니다. UID 10001 전용 Unix 소켓을 신규 볼륨에 만들며 TCP 수신 포트·Docker 소켓·DB 자격정보가 없습니다. 백엔드는 DB URL의 계정·비밀번호·DB명을 유지하고 호스트만 이 소켓으로 대체합니다. PostgreSQL 컨테이너 IP 변경에 의존하지 않습니다. 기존 컨테이너와 네트워크는 수정하지 않습니다. 초기 검증용 restart 정책은 `no`입니다.

인증 API는 `nas-host:8010`이며 이 이름을 확인된 게이트웨이 `172.17.0.1`에 고정합니다. 이 정확한 HTTP 주소만 내부 예외로 허용합니다. NAS 방화벽에서 신규 네트워크의 접근이 차단되면 중단하고 보고합니다. `.env`는 소유자만 읽는 600 권한을 유지하고, 실제 handoff/frontend origin을 확인하기 전에는 예제의 빈 값을 채우지 않습니다. handoff 키는 기존 인증 서버의 전용 키와 같아야 하며 JWT 키와는 별개입니다.

NAS의 `new-scm` 디렉터리에서 backend requirements가 설치된 Python으로 `python3 deploy/preflight.py`를 실행합니다. 서비스 시작 없이 Compose, 환경설정, 포트, 기존 프로세스, DB 읽기 전용 권한, 54개 테이블, revision, subject 3 → SCM 사용자 1 매핑과 grant, 인증 API를 검사합니다. 설정 출력은 메모리에서만 처리하며 비밀값·원본 오류는 출력하지 않습니다. `--config-only`는 NAS 실연결 검사를 생략합니다. 호스트 검사가 통과해도 컨테이너 네트워크·소켓 볼륨·실제 Nginx·공유 키 일치·브라우저 SSO는 별도 검증 대상입니다.

다른 PC의 초기 접근은 SSH의 `-L 127.0.0.1:8011:127.0.0.1:8011` 포워딩을 사용합니다. 통합 로그인도 시험하려면 같은 SSH 연결에 `-L 127.0.0.1:3010:127.0.0.1:3010`을 추가하고 두 사이트를 같은 `127.0.0.1` 호스트로 접속해야 합니다. 로컬 포트 충돌을 먼저 확인합니다. 이때 확인된 브라우저 출처만 CORS/handoff/frontend 설정에 허용합니다. HTTP 개발 검증과 HTTPS 운영 설정은 구분합니다.

기존 SCM 버튼의 빌드 설정 `VITE_SCM_API_URL` / `VITE_SCM_FRONTEND_URL`은 신규 프론트엔드의 동일 출처 Nginx를 가리켜야 합니다. 기존 기본값 8012/5174로는 이 구성을 사용할 수 없습니다. 기존 설정은 변경하지 않았으며 확인·필요한 변경은 별도 승인 대상입니다. 세션은 단일 프로세스 메모리에 저장되고 30분 후 만료됩니다. 원본 로그아웃의 즉시 전파는 미구현입니다. 업무 API는 여전히 미구현이며 `system.access`만으로 모든 업무 메뉴가 열리지는 않습니다.

모든 사전 확인과 사용자 승인 후에만 다음을 실행합니다. 이번 작업에서는 실행하지 않았습니다. `config`는 반드시 `--quiet`로 실행하고 `--environment` 또는 전체 `inspect` 출력은 사용하지 않습니다.

```sh
docker compose --project-name new-scm --env-file .env -f deploy/compose.yaml config --quiet
python3 deploy/preflight.py
# 미해결 항목 검토 및 사용자 승인 후 신규 프로젝트만 실행
docker compose --project-name new-scm --env-file .env -f deploy/compose.yaml up -d --build db-relay backend frontend
```

## 주의

- backend/, frontend/ 원본, 기존 .env는 변경하지 않았습니다.
- asset_manager_dev에 접속하지 않았습니다.
- new_scm_dev의 스키마를 변경하지 않습니다. Alembic 자동 실행 코드가 없습니다.
- NAS 접속과 배포는 진행하지 않았습니다.
