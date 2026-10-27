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

.env의 SCM_DATABASE_URL은 비어 있습니다. DB 점검이 필요하면 기존 backend/.env 값을 재사용하지 말고 new_scm_dev 전용 읽기 권한 계정의 URL을 새 파일에만 설정하세요. 비밀번호를 명령행이나 보고서에 넣지 마세요. 접속 코드가 DB명을 검증하고 세션에 default_transaction_read_only=on 및 statement_timeout을 적용합니다. DB 상태 API는 실제 read_only=on을 확인한 후에만 테이블 수를 반환합니다.

## 배포 준비

deploy/compose.yaml은 신규 Compose 프로젝트 범위의 네트워크와 신규 전용 볼륨 경로를 사용하며 기본 공개 포트는 127.0.0.1:8011입니다. 기존 컨테이너·네트워크·볼륨을 참조하지 않습니다. restart: unless-stopped는 향후 배포 시 자동 재시작용입니다. 지금은 Compose 구문만 검증했고 컨테이너를 생성하거나 실행하지 않았습니다.

NAS 배포 전에 CPU 아키텍처, Docker/Compose 버전, 8011 포트 사용 여부, DB 컨테이너 또는 호스트에 대한 네트워크 경로, 신규 DB 읽기 권한 계정, 로그·업로드 폴더 쓰기 권한, 프록시·TLS·접근 통제, 정적 파일 인증, 운영 백업 정책을 확인해야 합니다. 컨테이너의 127.0.0.1은 NAS 호스트의 127.0.0.1과 다르므로 DB URL의 호스트를 별도 확인해야 합니다. 기존 PostgreSQL 데이터 디렉터리를 신규 컨테이너에 마운트하지 마세요.

현재 프론트엔드는 mock 사용자와 mock 업무 데이터를 사용하므로 운영 사용자에게 공개하거나 실제 업무 데이터를 연결할 수 없습니다. 4단계에서 인증·권한·업무 API·감사 기록을 구현한 뒤에만 배포를 검토하세요.

## 주의

- backend/, frontend/ 원본, 기존 .env는 변경하지 않았습니다.
- asset_manager_dev에 접속하지 않았습니다.
- new_scm_dev의 스키마를 변경하지 않습니다. Alembic 자동 실행 코드가 없습니다.
- NAS 접속과 배포는 진행하지 않았습니다.
