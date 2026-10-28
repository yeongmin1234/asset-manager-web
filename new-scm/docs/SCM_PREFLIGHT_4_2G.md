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
필수 메모리 제한, 지원 여부에 따른 CPU/PID 제한, 로그 드라이버 none, 자동 삭제 조건으로 실행한다.
Docker CLI 시간 초과 시 고유한 `scm-preflight-*` 이름의 검증 컨테이너만 강제 정리한다.
기존 컨테이너 이름을 정리 대상으로 사용하지 않는다. Docker 데몬 장애·호스트 종료 시
정리를 보장할 수 없으며, 이 경우 해당 검증 컨테이너의 잔존 여부를 확인해야 한다.

## 1. NAS에서 컨테이너 없이 설정만 확인

`new-scm` 디렉터리에서 기존 `.env` 소유자로 실행한다. `.env`의 기존 600 권한을
확인하며 스크립트가 파일·권한을 수정하지 않는다. `sudo`로 Python만 실행하면 소유자
검사가 실패한다. `SUDO_USER`/`SUDO_UID`로 소유자 검사를 우회하지 않는다.
전체 검사에는 호스트 `ss` 또는 `netstat`도 필요하다.

```sh
cd '/volume6/총무/서버/자산관리 프로젝트/asset-manager-web/new-scm'
docker compose version --short
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py --config-only
```

NAS IP HTTP origin을 사용하는 경우 `browser_http_requires_local_tunnel`로
실패해야 정상이다. 이번 코드 수정은 이를 허용하지 않는다. `--config-only`는 이미지
빌드·Pull·컨테이너 실행·DB/API 연결을 하지 않는다. Compose의 해석된 설정과 정책을
검사하지만 NAS DB나 실제 SSO 성공을 의미하지 않는다.

### Docker 데몬 조회만 sudo가 필요한 NAS

스크립트 자체는 반드시 `.env` 소유자 `yeong00o`로 실행한다. `--docker-sudo`를 추가해도
Compose `version/config`, `.env` 읽기와 소유자·600 검사, 리스너 조회는 일반 사용자 권한이다.
이 단계는 Docker 데몬에 접근하지 않으므로 `--config-only`에 sudo 인증이 필요하지 않다.

전체 검사는 아래 최종 명령으로 실행한다. **신뢰할 수 있는 최신 검증 이미지가 이미
로드되어 있어야 한다.** 원격 명령 전달용 비대화형 SSH가 아니라 사용자 터미널에서 실행한다.
필요하면 `ssh -t -p 9680 yeong00o@192.168.222.210`으로 터미널을 확보한다.

```sh
cd '/volume6/총무/서버/자산관리 프로젝트/asset-manager-web/new-scm'
if sudo -v 2>/dev/null; then
  PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py \
    --docker-sudo --isolated-image new-scm-preflight:4-2g
else
  printf 'FAIL docker_sudo_authentication_failed\n'
fi
```

`sudo -v`의 암호는 sudo가 터미널에서 직접 받는다. Python은 암호를 입력받거나 저장하지
않으며 `sudo -S`, askpass, 암호 환경변수, `sudo python3`, 비밀번호 없는 sudo 설정을 쓰지 않는다.
인증은 같은 터미널에서 먼저 완료해야 한다. 이후 스크립트의 sudo는 모두 `-n`이므로
인증이 없거나 만료되면 재입력·자동 우회 없이 고정 코드로 중단한다.

승격할 수 있는 명령은 고정된 `docker info --format`, 기존 PostgreSQL의 선택된 상태
필드와 bridge 조회, 로컬 검증 이미지 ID 조회, 제한된 `scm-preflight-*` 검증 컨테이너
실행·정리뿐이다. 전체 inspect, 기존 컨테이너 rm/restart, Compose up, 임의 컨테이너
실행은 명령 허용 목록에서 거부한다. 이 제한은 스크립트의 호출 범위이며 NAS sudoers
정책을 새로 설정하는 것은 아니다. sudo와 Docker 실행 파일도 root 소유이며 그룹/다른
사용자가 쓰지 못하는 실제 경로인지 확인한다. 이 조건이 안 맞으면 권한을 바꾸지 않고 중단한다.

데몬 호출은 `unix:///var/run/docker.sock`을 명시하고 다른 Docker context/endpoint 환경을
제외한다. 소켓 자체의 권한·소유자, 사용자 그룹, sudoers는 바꾸지 않는다. 검증 컨테이너에는
sudo 옵션을 전달하지 않으며 내부 UID는 계속 10001이다. DB URL은 sudo 암호 입력과
섞이지 않는 stdin 파이프로만 전달한다. 기존 sudo I/O 감사가 stdin을 기록하는 환경에서는
그 입력도 감사 대상일 수 있다. 감사 설정은 스크립트가 변경하지 않는다.

주요 고정 실패 코드는 다음과 같다. 실제 stdout/stderr와 비밀값은 보고하지 않는다.

- `docker_sudo_command_failed`: sudo 인증/권한 또는 Docker 조회 실패. 사용자가 같은 터미널에서 인증·권한을 확인해야 한다.
- `docker_sudo_executable_missing` / `docker_sudo_executable_untrusted`: 필요한 신뢰 가능한 실행 파일을 사용할 수 없음.
- `docker_sudo_or_verifier_failed`: 승격된 실행 또는 검증 컨테이너가 알려진 정책 코드 없이 실패함.
- `isolated_verifier_cleanup_failed`: 시간 초과/CLI 장애 후 임시 컨테이너 정리를 확인하지 못함. 자동 재시도·배포를 중단한다.

정상 종료한 검증 컨테이너는 `--rm`으로 삭제된다. 시간 초과나 Docker CLI 장애가 있으면
해당 실행의 고유 이름만 `sudo -n docker rm --force`로 정리한다. 인증 만료 등으로 이 정리도
실패하면 같은 터미널에서 사용자가 다시 인증하고 `scm-preflight-*` 잔존 여부를 조회해야 한다.
기존 PostgreSQL이나 자산관리 컨테이너를 정리하지 않는다.

### Synology CPU CFS / PID 제한 호환성

임시 검증 컨테이너를 실행하기 전에 같은 로컬 Docker 데몬에 `info --format`을 조회한다.
선택하는 필드는 `CPUCfsPeriod`, `CPUCfsQuota`, `PidsLimit`, `MemoryLimit` 네 개의
boolean뿐이다. 전체 Docker 정보, 환경변수, 원본 오류는 출력하지 않는다. `--docker-sudo`를
사용하면 이 조회도 기존 허용 목록과 `sudo -n` 경로를 따른다. 시험 컨테이너를 띄우거나
커널·cgroup·Docker 설정을 바꾸지 않는다.

- CPU period와 quota가 **모두 true**이면 `--cpus=1`을 유지한다. 하나라도 false이면
  이 옵션만 제외하고 `WARN verifier_cpu_limit_unsupported`를 출력한다.
- PID 지원이 true이면 `--pids-limit=64`를 유지한다. false이면 이 옵션만 제외하고
  `WARN verifier_pid_limit_unsupported`를 출력한다.
- 하나라도 제외하면 `WARN verifier_resource_limits_incomplete`를 함께 출력한다.
  이는 **CPU/PID 자원 제한이 완전히 적용되지 않은 상태**이며, DB/API 조회가 PASS여도
  자원 격리가 완전하게 적용되었다는 의미가 아니다.
- JSON/필드가 없거나 boolean이 아닌 등 지원 여부를 확인하지 못하면
  `FAIL verifier_resource_capabilities_invalid`로 컨테이너 실행 전에 중단한다.
  조회 자체의 권한·통신 실패도 기존 고정 실패 코드로 중단하며 미지원으로 추정하지 않는다.
- 메모리 지원이 false이면 `FAIL verifier_memory_limit_unsupported`로 중단한다.
  `--memory=256m`은 호환성을 이유로 제거하지 않는다.

CPU/PID 지원 플래그의 모든 조합에서도 `--read-only`, `--cap-drop=ALL`,
`--security-opt=no-new-privileges:true`, UID 10001, 메모리 제한, 제한된 tmpfs는 유지한다.
필수 보안 옵션을 제거한 실행 명령은 허용 목록에서 거부한다. Docker가 지원한다고
보고했는데 실행이 실패하는 경우에는 stderr 내용으로 추정해 옵션을 제거하거나 자동
재시도하지 않는다. 데몬의 지원 보고에 따른 선택이며 실제 컨테이너의 cgroup 강제 적용을
별도로 측정한 결과는 아니다. 이번 변경에서 NAS 컨테이너 실행은 수행하지 않았다.

NAS 실행 명령은 위의 `sudo -v`와 `--docker-sudo --isolated-image` 명령 그대로다.
수정된 스크립트와 같은 내용으로 검증 이미지를 다시 준비해야 한다. `--config-only`는
이 자원 지원 조회도 하지 않으며 Python 3.8 표준 라이브러리만으로 기존처럼 실행된다.

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
# 이미지 로드는 별도 준비 작업. Docker 권한이 필요한 NAS에서는 sudo를 사용한다.
sudo docker load -i /검토한/전송경로/new-scm-preflight-4-2g.tar
PYTHONDONTWRITEBYTECODE=1 python3 deploy/preflight.py \
  --isolated-image new-scm-preflight:4-2g
```

로컬 이미지를 immutable ID로 확인하고 `--pull=never`로 실행하므로 NAS에서 자동으로
이미지를 받거나 빌드하지 않는다. NAS 소스와 이미지의 preflight 내용이 다르면 DB 접속
전에 `verifier_script_mismatch`로 중단한다(CRLF/LF 차이는 무시).
sudo 및 Synology 자원 제한 지원 수정도 이미지 안의 preflight에 반영되도록 검증 이미지를 다시 만들어야 한다.
Docker 권한이 제한된 NAS에서는 위의 `sudo -v`와 `--docker-sudo` 최종 명령을 사용한다.

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

origin 정책 불일치가 있으면 배포 차단 사유다. NAS 실연결, 검증 이미지의 실제 실행,
컨테이너 내부 DB 릴레이/Unix 볼륨/Nginx, 공유 키 일치, 브라우저 SSO는 아직 별도 검증
대상이다. 전체 검사 PASS도 실제 SCM 서비스 배포 승인으로 취급하지 않는다.

- [MDN Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie): SameSite와 Secure, cross-origin fetch의 credentials 조건.
- [Docker host network](https://docs.docker.com/engine/network/drivers/host/): Linux host 네트워크 공유와 포트 공개의 관계.
- [Docker run](https://docs.docker.com/engine/containers/run/): 읽기 전용 루트, capability 및 리소스 제한.
- [Docker 자원 제한](https://docs.docker.com/engine/containers/resource_constraints/): 커널 기능 지원과 `docker info` 조회.
- [Docker Engine 20.10 Info 타입](https://github.com/moby/moby/blob/v20.10.24/api/types/types.go): CPU CFS·PID·메모리 지원 boolean 필드.
- [sudo 공식 매뉴얼 원본](https://github.com/sudo-project/sudo/blob/main/docs/sudo.man.in): 터미널 암호 입력, `-v` 인증 캐시와 `-n` 비대화형 실행.
