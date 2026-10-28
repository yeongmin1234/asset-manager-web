# 4-2G NAS 사전 검증: Python 3.8 호스트와 Python 3.12 검증 환경

## 실행 경계

NAS Python 3.8.15, 기존 서비스, PostgreSQL, 실제 `.env`를 변경하지 않는다.
설정 검사는 NAS Python의 표준 라이브러리와 호스트 Docker Compose CLI만 사용한다.
기존 구현은 `--config-only`에서도 SQLAlchemy 및 Python 3.10+ 문법을 사용하는 백엔드
모듈을 불러왔다. 이 의존성을 제거했다. 필수 명령 부재·시간 초과·JSON 오류·런타임
버전 및 의존성 부족은 비밀값이 없는 고정 오류 코드로 구분한다. 원본 예외와 Compose
출력은 계속 숨긴다.

DB/API 전체 검사는 선택적인 **일회성 검증 컨테이너**에서 실행한다.
Compose, `ss`/`netstat`, 기존 컨테이너 상태 조회는 NAS 호스트 Python이 담당한다.
검증 컨테이너에는 Docker CLI·Docker 소켓·호스트 디렉터리·`.env`를 마운트하지 않는다.
DB URL만 stdin 파이프로 전달하며 handoff/diagnostics/JWT 키는 전달하지 않는다.
호스트 네트워크는 `127.0.0.1:15432` 및 인증 API에 조회로 접속하기 위해 사용한다.
수신 서버, 포트 공개, SCM 서비스 실행, 스키마 변경은 없다.

컨테이너는 비루트 UID 10001, 읽기 전용 루트, capability 제거, no-new-privileges,
메모리/CPU/PID 제한, 로그 드라이버 none, 자동 삭제 조건으로 실행한다.
Docker CLI 시간 초과 시 고유한 `scm-preflight-*` 이름의 검증 컨테이너만 강제 정리한다.
기존 컨테이너 이름을 정리 대상으로 사용하지 않는다. Docker 데몬 장애·호스트 종료 시
정리를 보장할 수 없으며, 이 경우 해당 검증 컨테이너의 잔존 여부를 확인해야 한다.

## 1. NAS에서 컨테이너 없이 설정만 확인

`new-scm` 디렉터리에서 기존 `.env` 소유자로 실행한다. `.env`의 기존 600 권한을
확인하며 스크립트가 파일·권한을 수정하지 않는다. `sudo`로 Python만 실행하면 소유자
검사가 실패할 수 있다. Docker 조회 권한과 호스트 `ss` 또는 `netstat`도 필요하다.

```sh
cd '/volume6/총무/서버/자산관리 프로젝트/asset-manager-web/new-scm'
docker compose version --short
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --config-only
```

현재 알려진 `.env`의 NAS IP HTTP origin은 `browser_http_requires_local_tunnel`로
실패해야 정상이다. 이번 코드 수정은 이를 허용하지 않는다. `--config-only`는 이미지
빌드·Pull·컨테이너 실행·DB/API 연결을 하지 않는다. Compose의 해석된 설정과 정책을
검사하지만 NAS DB나 실제 SSO 성공을 의미하지 않는다.

## 2. Python 3.12 전용 이미지 준비

확보된 기본 Python 3.12 이미지에는 DB/API 검사 의존성이 없으므로 **기본 이미지만으로는
전체 검사가 안 된다**. Docker 사용이 가능한 별도 준비 PC에서 아래 검증 이미지를 만든다.
이번 변경에서 이 빌드나 컨테이너 실행은 수행하지 않았다.

```sh
# 별도 준비 PC, new-scm 디렉터리. NAS 서비스용 Compose를 사용하지 않는다.
docker build -f deploy/Dockerfile.preflight -t new-scm-preflight:4-2g .
docker save -o "$HOME/new-scm-preflight-4-2g.tar" new-scm-preflight:4-2g
```

루트 `.dockerignore`는 검증 빌드에 필요한 소스 3개와 Dockerfile만 허용한다.
실제 `.env`, 백업, 키, 사용자 데이터는 빌드 컨텍스트에서 제외한다. 이 ignore 파일은
기존 Compose의 `backend`/`frontend` 빌드 컨텍스트에 영향을 주지 않는다.
아카이브는 Git 프로젝트 밖의 전송 위치에 둔다. NAS와 준비 PC의 아키텍처가 같아야 한다.
기본 이미지·Python 패키지는 준비 PC에서 신뢰할 수 있는 경로로 확보해야 한다.

## 3. NAS 전체 조회 검사 — 일회성 검증 실행을 선택한 경우

검토한 검증 이미지 아카이브를 NAS의 프로젝트 밖 위치로 전송하고 로드한 후 실행한다.
이미지 로드는 이미지 저장소만 변경한다. 아래 명령은 SCM 배포가 아니지만 **임시 검증
컨테이너를 실제로 실행**하므로, 컨테이너를 전혀 실행하지 않는 단계에서는 1번만 사용한다.

```sh
docker load -i /검토한/전송경로/new-scm-preflight-4-2g.tar
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py \
  --isolated-image new-scm-preflight:4-2g
```

로컬 이미지를 immutable ID로 확인하고 `--pull=never`로 실행하므로 NAS에서 자동으로
이미지를 받거나 빌드하지 않는다. NAS 소스와 이미지의 preflight 내용이 다르면 DB 접속
전에 `verifier_script_mismatch`로 중단한다(CRLF/LF 차이는 무시).

검사 대상은 `new_scm_dev` / `new_scm_ro`뿐이다. 모든 SQL은 SELECT이며 연결 시
`default_transaction_read_only=on`, 연결/문장 시간 제한을 지정한다. 54개 테이블,
revision `20261027_0013`, subject 3 → SCM 사용자 1의 활성 매핑과 `system.access`,
쓰기·소유자·상위 권한 부재를 확인한다. 인증 API는 루프백과 확인된 게이트웨이에서
OpenAPI를 GET하여 경로만 확인하고, 코드 발급·교환·로그인 POST는 하지 않는다.
기존 보호 포트와 `asset-postgres`의 상태를 검사 전후 비교하며 실패 경로에서도 비교한다.

기존 `.env`는 그대로 읽는다. origin 정책 검사 실패 시 임시 컨테이너조차 시작하지 않는다.
필요하다면 별도 검토한 600 권한의 `.preflight.env`를 `--env-file .preflight.env`로 지정할
수 있다. 이 파일은 Git 제외 대상이며 원본을 덮어쓰지 않는다. 별도 파일의 PASS는 원본
`.env`의 검증이나 실제 배포 설정의 PASS를 대신하지 않는다. 스크립트는 이 파일도 생성하지 않는다.

## 브라우저 접속 구성과 인증 정책

현재 `http://192.168.222.210:3010`과 `http://127.0.0.1:8011`은 호스트가 다르다.
브라우저의 `127.0.0.1`은 사용자 PC이며 NAS가 아니다. 이 조합의 cross-site fetch는
`SameSite=Lax` 쿠키 인증과 맞지 않는다. CORS만 추가해도 해결되지 않는다.
쿠키를 `SameSite=None`으로 바꾸거나 HTTP NAS IP를 허용하는 완화는 하지 않는다.

초기 개발 검증에는 사용자 PC에서 두 로컬 터널을 함께 사용한다. 로컬 포트 충돌이 있으면
중단한다. 이는 NAS의 기존 포트 바인딩을 변경하지 않는다.

```sh
ssh -p 9680 -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:3010:127.0.0.1:3010 \
  -L 127.0.0.1:8011:127.0.0.1:8011 yeong00o@192.168.222.210
```

검토할 값은 아래와 같다. **이번 작업은 기존 `.env`에 이 값을 쓰지 않는다.**

```dotenv
SCM_ENV=development
SCM_HANDOFF_ORIGIN=http://127.0.0.1:3010
SCM_FRONTEND_ORIGIN=http://127.0.0.1:8011
```

두 URL은 다른 origin(포트 차이)이지만 같은 site(동일 scheme/host)다. CORS는 확인된
origin만 허용하고 credentials를 유지한다. `localhost`와 `127.0.0.1`을 섞지 않는다.
운영 구성은 기존 정책대로 같은 HTTPS 호스트의 확인된 두 origin을 사용한다. 예를 들어
`https://portal.example:443`과 `https://portal.example:8443`은 정책 형식을 설명하는 예이며
실제 배포 주소가 아니다. 서로 다른 서브도메인을 자동 허용하는 정책 변경도 하지 않았다.

기존 자산관리의 SCM 버튼 대상 URL, 프런트엔드 빌드 설정, 출처 검사와 전용 handoff 키가
이 접속 방식과 실제로 맞는지는 별도 확인이 필요하다. 기존 자산관리 소스·설정·서비스는
이번 작업에서 수정하지 않는다. 신규 8011 서비스는 아직 배포하지 않았으므로 터널만으로
신규 화면이나 로그인 성공을 보장하지 않는다.

## 남은 검증과 근거

현재 NAS의 origin 정책 불일치는 배포 차단 사유다. NAS 실연결, 검증 이미지의 실제 실행,
컨테이너 내부 DB 릴레이/Unix 볼륨/Nginx, 공유 키 일치, 브라우저 SSO는 아직 별도 검증
대상이다. 전체 검사 PASS도 실제 SCM 서비스 배포 승인으로 취급하지 않는다.

- [MDN Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie): SameSite와 Secure, cross-origin fetch의 credentials 조건.
- [Docker host network](https://docs.docker.com/engine/network/drivers/host/): Linux host 네트워크 공유와 포트 공개의 관계.
- [Docker run](https://docs.docker.com/engine/containers/run/): 읽기 전용 루트, capability 및 리소스 제한.
