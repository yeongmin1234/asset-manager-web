# 3단계 로컬 검증 기록 — 2026-10-27

- 기존 backend/frontend 보호 대상 3,662개 파일의 SHA-256 집계가 작업 전후 동일했습니다.
- 신규 FastAPI /health: HTTP 200, ok=true.
- 백엔드 단위 테스트 4개 통과 (`python -m unittest discover -s tests -v`).
- 신규 /api/v1/system/status: HTTP 200, service=new-scm.
- /api/v1/system/db-status: 키 없이 HTTP 403.
- 유효한 로컬 키, DB URL 미설정: HTTP 503, database_unavailable. DB SELECT는 수행되지 않았습니다.
- 프론트엔드: Vite 빌드 성공, 91개 모듈 변환.
- 로컬 브라우저: 화면 제목, 최상위 메뉴 12개, 신규 SCM API 연결 표시 확인. 외부 요청 0건.
- 최종 프론트엔드 독립 복사본 재빌드 성공(91개 모듈), 브라우저 재검증에서 API 연결 표시 확인 및 외부 요청 0건.
- Vite 프록시 GET /api/v1/system/status: HTTP 200.
- Compose: 네트워크 이름을 프로젝트 범위로 설정한 뒤 `docker compose config --quiet` 성공. 이미지 빌드와 NAS 실행은 미검증.
- new_scm_dev 연결·테이블 수·DB 읽기 전용 세션은 인증 정보가 없어 미검증.
- 기존 자산관리 DB·NAS·기존 Docker 컨테이너에 접근하지 않았습니다.
