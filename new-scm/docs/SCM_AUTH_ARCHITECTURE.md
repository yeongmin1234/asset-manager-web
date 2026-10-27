# 신규 SCM 인증 구조 분석 (4-2단계)

2026-10-27 정적 코드 분석. 기존 자산관리 코드와 DB는 읽기 전용 참고만 했다.

## 기존 통합 로그인

1. `frontend/src/main.jsx`가 `/login`에서 기존 로그인 컴포넌트를 표시하고 `frontend/src/api/client.js`의 `POST /auth/login`을 호출한다.
2. 기존 백엔드 `backend/app/api/routers/auth.py`가 기존 자산관리 DB의 `users`를 확인하고 HS256 JWT를 발급한다. JWT에는 `sub`(기존 사용자 ID), `username`, `role`, `iat`, `exp`가 있다. 기본 유효기간은 `backend/app/core/config.py`의 480분 설정이다.
3. 브라우저는 토큰을 원본 프론트엔드 origin의 `localStorage` 키 `assetManager.accessToken`에 저장한다. API 요청은 `Authorization: Bearer` 헤더를 보낸다. 인증 쿠키·서버 세션·자동 갱신 경로는 확인되지 않았다.
4. 기존 `backend/app/core/auth.py`는 HS256 서명과 `exp`를 검증하고, 매 요청에서 기존 DB의 사용자 존재 및 `is_active`를 확인한다. `GET /auth/me`는 같은 검증으로 현재 사용자를 돌려준다. `role=admin` 또는 `menu_permissions`로 기존 API의 접근을 제한한다.
5. 로그인 성공 후 `/select-system`으로 이동한다. `frontend/src/components/system/SystemSelectPage.jsx`는 기존 사용자 `role`/`menu_permissions`에서 산출된 SCM 선택 가능 여부를 사용한다. SCM 선택 시 원본 `frontend/src/App.jsx`가 `ScmSiteLayout`을 렌더하고 같은 origin의 `/scm-preview/index.html`을 iframe으로 연다. 독립 `new-scm/frontend` 개발 서버로 이동하지 않는다.
6. 기존 로그아웃 API는 접근 로그를 남긴다. 브라우저는 토큰을 지운다. JWT 폐기 목록이나 서버 측 즉시 무효화는 확인되지 않았다. 만료/401에는 원본 프론트엔드가 토큰을 지우고 `/login`으로 보낸다. 명시적 갱신 API는 없다.

## 독립 SCM 연동 판정: C안

- A안: 기존 `/auth/me`는 HS256 서명·만료와 DB의 활성 사용자까지 검증하는 **실제 토큰 검증 API**다. 신규 SCM 백엔드가 Bearer를 서버 간 HTTPS/신뢰 가능한 내부 경로로 보내면 응답의 사용자 `id`를 신뢰할 수 있다. 하지만 현재 원본 선택 화면은 독립 SCM에 일회성·단기 인증값이나 원본 Bearer를 전달하지 않는다. 기존 비밀키를 SCM에 복사해 독자 검증하는 방식은 금지된다.
- B안: 원본의 `/scm-preview`는 기존 출처의 정적 미리보기로, 독립 `new-scm/frontend` 빌드가 아니다. 원본 라우팅/배포를 변경하지 않고는 기존 버튼에서 독립 앱을 제공할 수 없다. 같은 출처로 제공해도 신규 백엔드 검증은 필요하다.
- 따라서 기존 통합 로그인과 독립 SCM의 인증 연동은 **미완료**다. 기존 통합 화면의 iframe 미리보기는 고정 사용자 Mock을 쓰며, 화면 진입은 신규 SCM 백엔드 인증을 입증하지 않는다.

## 이번 구현의 경계

- `backend/app/core/auth.py`: `AuthVerifier` 인터페이스와 기본 `UnconnectedVerifier`. 미설정·위조·만료·비활성·검증기 오류는 401로 닫힌다. 현재 실제 통합 토큰 검증기는 없다.
- `backend/app/core/permissions.py`: 검증된 주체의 `system.access`, 메뉴 grant, API 행위 grant, 관리자 조건을 별도 검사한다. 부족한 권한은 403이다. 클라이언트의 사용자 ID/역할 헤더를 읽지 않는다.
- `backend/app/main.py`: `GET /api/v1/auth/me`가 공통 인증/시스템 권한 의존성을 사용하는 유일한 신규 인증 API다. 기본 검증기는 항상 거부하므로 실제 운영 계정의 200 응답은 불가능하다.
- 아직 구현되지 않은 `/api/v1/*` 경로도 fallback에서 인증을 먼저 요구한다. 미연결 상태는 401, 테스트 주입으로 인증/시스템 권한을 통과해도 업무 응답은 404다.
- `frontend/src/contexts/AuthContext.jsx`, `frontend/src/App.jsx`: 독립 SCM의 고정 관리자 Mock을 제거하고 모든 업무 화면을 차단한다. 로그인 상태가 확인되지 않은 동안 업무 컴포넌트와 데이터가 렌더되지 않는다.
- 공개 상태 API `/health`, `/api/v1/system/status`는 유지했다. `/api/v1/system/db-status`의 진단 키 정책도 유지했다.

## 미해결 사항

1. 기존 인증 서버가 신규 SCM에 검증 가능한 일회성 코드 또는 단기 토큰을 발급하는 공식 경로, 전달 방식과 허용 origin을 결정해야 한다. 기존 시스템 수정이 불가피하다면 이 단계의 보호 조건 아래서는 진행할 수 없다.
2. 외부 인증 주체와 `new_scm_dev.users` 간 안전한 식별 매핑, 비활성화 동기화, 세션 만료/로그아웃 즉시 무효화, 재사용 방지, 감사 로그 정책을 정해야 한다.
3. `users`의 `account_type=admin|employee`, `status=active|suspended` 외 메뉴/API 권한과 외부 사용자 연결 컬럼은 없다. 실제 행 데이터나 비밀번호 해시 형식은 확인하지 않았다.
4. 원본 SCM iframe과 독립 SCM은 별개 빌드다. 이번 변경은 원본 iframe 복사본에 적용되지 않는다. 기존 시스템을 수정하지 않는 조건에서는 원본 선택 버튼이 독립 SCM으로 연결되지 않는다.

## 기존 인증 API 상세 계약

| 항목 | 정적 분석 결과 |
|---|---|
| 발급 | `POST /auth/login`은 기존 `users.username`을 조회하고 비밀번호 및 `is_active`를 확인한 뒤 Bearer JWT를 발급한다. |
| 서명 | `backend/app/core/auth.py`의 `jwt.encode(..., algorithm="HS256")`와 `jwt.decode(..., algorithms=["HS256"])`. JWT에는 `sub`(기존 사용자 숫자 ID의 문자열), `username`, `role`, `iat`, `exp`가 있다. 신규 SCM은 기존 비밀키를 가져오지 않는다. |
| 만료·갱신 | `AUTH_TOKEN_MINUTES` 기본 480분. PyJWT가 `exp`를 검증한다. 명시적인 `aud`/`iss`/`jti`와 갱신 API는 확인되지 않았다. |
| 현재 사용자 | `GET /auth/me`는 `Authorization: Bearer <JWT>`를 요구한다. 서명·만료 검증 후 `sub`의 사용자를 기존 DB에서 다시 조회하고 `is_active`를 확인한다. 응답은 `id`, `username`, `name`, `role`, `is_active`, `menu_permissions`를 포함한다. 전달된 ID를 단순 반환하는 API가 아니다. |
| 로그아웃 | `POST /auth/logout`은 유효한 Bearer를 요구하고 접근 로그를 남긴다. 원본 프론트엔드는 로컬 토큰을 제거한다. 서버 측 JWT 폐기 목록이 없어 만료 전 토큰의 즉시 무효화는 보장되지 않는다. |
| 브라우저 호출 | 기존 프론트엔드는 8010 백엔드에 Bearer 요청을 보낸다. 허용 출처는 기존 백엔드 CORS 목록에 제한된다. CORS는 서버 간 통신에 적용되지 않으며 인증 근거가 아니다. |

`localStorage`는 출처별로 격리된다. 같은 호스트라도 포트가 다른 독립 SCM 앱은 기존 `assetManager.accessToken`을 읽을 수 없다. 기존 iframe은 같은 출처에 있지만 현재 독립 SCM 빌드가 아니며, 임의의 토큰 전달 스크립트를 넣을 수 없다. 장기 JWT를 URL 쿼리나 신규 앱 저장소에 복사하면 노출 범위가 커진다.

기존 백엔드의 CORS 목록은 기존 프론트엔드 출처 위주이며 독립 개발 출처 `127.0.0.1:5174`는 기본 허용 목록에 없다. 브라우저에서 기존 8010 API를 직접 호출하면 Origin/사전 요청 정책의 영향을 받는다. 반면 신규 SCM의 Vite 프록시와 향후 서버 간 `/auth/me` 호출은 브라우저 CORS 바깥에 있다. 신규 프론트엔드는 자체 `/api/v1`로 요청하도록 설정되어 있으나 현재 신규 API의 인증 연동은 없다. CORS를 넓히는 것만으로 토큰 인계나 사용자 신뢰 문제가 해결되지 않는다.

`/auth/me` 응답은 별도로 서명되지 않는다. 서버 간 검증을 구현할 경우 고정된 인증 서버 주소, TLS 인증서 또는 검증된 내부 경로, 리디렉션 금지, 짧은 타임아웃, 응답 형식 검증 및 오류 시 401이 필요하다. 원본 `menu_permissions`의 `scm_app`은 기존 미리보기 진입 권한이며 SCM 업무/API/관리자 grant가 아니다.

## 사용자 연결과 권한 차이

기존 고유 식별자는 `/auth/me`의 `id`다. `SCM_DB_CATALOG.md`의 `new_scm_dev.users`는 별도 자체 `id`, 고유 `username`, `account_type` 및 `status`를 갖지만 외부 주체 키가 없다. 두 ID가 같다는 근거가 없고 실제 행은 조회하지 않았다. 이름·이메일·동일 숫자 ID로 자동 연결하지 않는다.

제안하는 신규 구조는 고정된 `issuer`와 기존 사용자 `subject`의 고유 쌍을 `users.id`에 연결하는 외부 주체 매핑, 그리고 별도 사용자/역할 grant 및 행 범위 저장소다. 매핑 활성 상태, `users.status=active`, `system.access`, 메뉴·행위 grant를 서버가 확인해야 한다. `account_type=admin`만으로 관리자가 되지 않는다. 이는 설계 제안이며 DB 마이그레이션/데이터 변경은 수행하지 않았다. `new_scm_ro`는 읽기 전용으로 유지한다.

원본 로그아웃 이벤트는 별도 출처의 독립 앱에 자동 전파되지 않는다. 신규 SCM 세션을 만들 경우 원본 로그아웃 후 JWT 유효기간과 SCM 세션 폐기 지연을 명시적으로 해결해야 한다. 계정 중지와 토큰 만료는 이후 API 요청에서 거부되어야 한다. 신규 SCM 요청 로그는 메서드·경로·상태·소요시간만 기록하며 Authorization 값과 비밀키를 기록하지 않는다.

