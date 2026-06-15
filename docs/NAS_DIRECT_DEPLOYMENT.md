# NAS Direct Deployment Guide

9-2 단계 기준 운영 방향은 Docker 미사용 직접 실행입니다.

## 요약

- 실제 NAS 배포는 아직 하지 않습니다.
- 기존 서버, SCM, MySQL, NAS 서비스는 변경하지 않습니다.
- 자산관리 전용 Backend/Frontend 프로세스와 전용 DB만 사용합니다.
- 포트 `80`, `8080`은 사용하지 않습니다.

## 실행 순서 초안

1. NAS 전용 경로에 프로젝트 파일을 배치합니다.
2. `backend/.env` 또는 `deploy/.env`를 작성합니다.
3. `backend/.venv`를 만들고 의존성을 설치합니다.
4. `frontend`에서 `npm run build`를 실행합니다.
5. `chmod +x deploy/*.sh`를 실행합니다.
6. `deploy/start_all.sh`로 시작합니다.
7. `deploy/health_check.sh`로 점검합니다.

## 중지

```sh
deploy/stop_all.sh
```

## 로그

```sh
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/health_check.log
```

## 백업

DB 백업은 `deploy/backup_db.sh`를 기준으로 준비합니다. 실제 실행 전에는 운영 DB 정보와 백업 경로를 다시 확인합니다.
