# 신규 SCM — 독립 인증 / 4-2H

NAS 적용 전 최신 검증은 [4-2I 결과·적용 전/후 명령·승인 및 롤백 조건](docs/SCM_NAS_4_2I_VERIFICATION.md)을 따릅니다. `--phase pre-migration`은 기존 0013 DB를 조회만 하며 신규 인증 DB 준비를 PENDING으로 구분합니다. 실제 NAS 실행/DB 변경은 별도 승인 사항입니다.

작업 범위는 이 폴더뿐입니다. 기존 자산관리 로그인·인증 API, SSO/handoff, 공유 인증 키 없이 SCM 주소에서 직접 로그인합니다. 실제 NAS 배포·DB 변경·Git 커밋/Push는 수행하지 않았습니다.

## 구성

- FastAPI / Python 3.12: SCM 전용 로그인·로그아웃, 30분 만료 DB 세션, 관리자 로그인 계정 설정 API.
- React / Vite: 직접 로그인, 로그아웃, 세션 확인, 기존 메뉴별 권한, 실제 인증 계정 설정 화면.
- PostgreSQL `new_scm_dev`: 업무 조회는 `new_scm_ro`; 인증 쓰기는 별도 최소 권한 `new_scm_auth`.
- `public.users`의 기존 비밀번호·54개 public 테이블·사용자 매핑을 보존하고 `scm_auth` 스키마에만 인증 테이블 3개를 추가합니다.
- 기존 업무 화면은 유지합니다. 다수 업무 화면의 샘플 데이터/메모리 상태 및 미구현 업무 API는 그대로이며 실제 업무 CRUD 구현 완료를 의미하지 않습니다.

## 개발 실행

로컬 **테스트 DB**에 승인된 마이그레이션과 명시적으로 선택한 계정의 초기 비밀번호 설정을 먼저 진행합니다. 기본 비밀번호와 자동 생성 계정은 없습니다.

1. Python 3.12 가상환경에 `python -m pip install -r backend/requirements.txt`.
2. `.env.development.example`을 별도 `.env.development`로 준비하고 로컬 테스트 DB URL 두 개를 안전하게 입력합니다. NAS `.env`는 덮어쓰지 않습니다.
3. PowerShell 창 하나에서 `./run_backend.ps1` (127.0.0.1:8012, 코드 reload).
4. 다른 창에서 `./run_frontend.ps1` (127.0.0.1:5174, Vite HMR).
5. `http://127.0.0.1:5174`에서 SCM 전용 로그인. Ctrl+C로 개발 서버를 중지합니다.

개발과 NAS 설정은 별도 파일입니다. Windows는 해당 파일의 NTFS 접근 권한도 소유자 중심으로 제한하세요. Linux/NAS 검사는 일반 사용자 소유·600·심볼릭 링크 금지를 유지합니다.

## 검증

```sh
python -B deploy/run_tests.py
cd frontend
npm test
npm run build
```

일반 실행은 PostgreSQL·POSIX·Compose·이미지 검사를 환경에 따라 명시적으로 skip합니다. 전체 검증은 격리 로컬 PostgreSQL Unix socket, Compose 실행 파일, 새로 빌드한 검증 이미지 ID를 명시합니다.

```sh
python -B deploy/run_tests.py --postgres-socket /tmp/scm-standalone-pg-<임시ID> --compose-executable <Compose실행파일> --verifier-image sha256:<검증이미지ID>
```

PostgreSQL 테스트는 네트워크 없는 **빈 임시 클러스터** 전용입니다. NAS·기존 DB에서 실행하지 마세요. 테스트 러너는 DB 컨테이너를 만들지 않으며 SCM 서비스를 실행하지 않습니다. 이미지 옵션을 주면 비루트·network=none 검증 컨테이너 1개를 실행합니다.

## NAS 반영 준비

[독립 운영 전환 보고서 및 DB·백업·초기 관리자·NAS 검증 절차](docs/SCM_STANDALONE_4_2H.md)를 먼저 읽으세요.
[격리 기동·중지·롤백 및 승인 체크리스트](docs/SCM_NAS_4_2H_READINESS.md)는 독립 인증 기준으로 갱신했습니다.
이전 `SCM_AUTH_HANDOFF_4_2E.md`, `SCM_PREFLIGHT_4_2G.md` 등은 과거 연동 단계의 기록이며 현재 배포 설정으로 사용하지 않습니다.

Compose는 NAS 호스트 `127.0.0.1:8011`만 게시하고 API는 내부 8012로 통신합니다. DB relay는 UID 10001 전용 Unix 소켓으로 기존 호스트 loopback 15432에 연결합니다. Docker 소켓을 앱/검증 이미지에 마운트하지 않습니다. NAS CPU/PID 제한 미지원 감지·고정 진단·메모리 제한·비루트·read-only·cap-drop·no-new-privileges·tmpfs를 유지합니다.
