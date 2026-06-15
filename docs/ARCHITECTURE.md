# Architecture

사내 자산관리 시스템은 React + FastAPI + PostgreSQL 기반의 웹 시스템입니다. PC와 모바일 브라우저에서 사용할 수 있도록 반응형 웹을 우선 적용하고, 추후 PWA 확장 가능성을 열어둡니다.

## 구성

- Frontend: React + Vite
- Backend: FastAPI
- Database: 자산관리 전용 PostgreSQL
- Deploy: Docker Compose
- Server: Synology NAS

## Backend

FastAPI 앱은 라우터, 설정, DB 연결 준비 영역을 분리합니다. 현재 단계에서는 `/health`, `/health/db`만 제공합니다.

## Frontend

React 앱은 업무용으로 간결한 첫 화면과 백엔드 상태 확인 버튼을 제공합니다. API 주소는 `VITE_API_BASE_URL` 환경변수로 관리합니다.

## Database

SCM DB/MySQL은 사용하지 않으며 자산관리 전용 PostgreSQL을 별도 운영합니다. 현재는 `assets`, `asset_history`, `categories`, `departments` 모델 구조만 준비했고 실제 테이블 생성과 마이그레이션 실행은 다음 단계에서 진행합니다.
