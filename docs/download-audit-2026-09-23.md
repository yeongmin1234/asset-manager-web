# 다운로드 전수 점검 및 수정 결과 (2026-09-23)

## 1. 발견된 다운로드 기능 목록

검색 범위: `frontend/src`, `backend/app`, 기존 테스트, `deploy`의 실행/프록시 관련 코드. download, blob, createObjectURL, window.open/location, href, Content-Disposition, StreamingResponse, FileResponse, responseType, arraybuffer, attachment, filename을 검색했다. Axios 다운로드는 없었다.

| 화면 / 진입점 | 프론트 파일 | 기존 API (GET) | 기존 방식 / 문제 가능성 |
| --- | --- | --- | --- |
| 설치자료실 목록 | InstallLibraryPage.jsx, InstallLibraryList.jsx | /install-files/{id}/download | FileResponse → 전체 Blob → a.click → 즉시 revoke; 대용량 메모리, 무진행 표시, 중복 클릭 |
| 설치 체크리스트 | InstallChecklistPanel.jsx | 동일 | 목록과 같은 콜백, 같은 문제 |
| 공통 첨부파일 | AttachmentPanel.jsx | /attachments/{id}/download | FileResponse → Blob → 즉시 revoke, 중복 클릭 방지 없음 |
| PDF/이미지 미리보기 | AttachmentPanel.jsx | /attachments/{id}/preview | 기존 await 이후 window.open과 팝업 차단 문제를 제거하고 현재 화면 모달 미리보기로 변경 |
| 자산 Excel 내보내기 | App.jsx, AssetExcelTools.jsx | /assets/export/excel | StreamingResponse → Blob, 즉시 revoke, 기본 헤더 대기 제한 6초 |
| 자산 Excel 등록 양식 | AssetExcelTools.jsx | /assets/import/template | StreamingResponse → Blob, 즉시 revoke |
| 감사로그 Excel | AuditLogTab.jsx | /admin/audit-logs/export | StreamingResponse → Blob, 즉시 revoke |
| 인사계정 Excel 양식 | HrAccountListPage.jsx | /hr/accounts/import/template | StreamingResponse → Blob, 즉시 revoke, 버튼 잠금 없음 |

공통 첨부파일 사용 화면: 자산 상세, 거래처 연락처, 업무 매뉴얼, 법인차량, 화재보험, 만료 일정. 이 화면들의 문서/PDF/Excel 첨부 다운로드는 모두 동일 공통 수정 적용 대상이다.

별도 PDF 생성/내보내기 API는 없다. 설치자료실은 ZIP/EXE/MSI/7Z/PDF/TXT/BAT/PS1을 지원하며 다운로드 경로는 같다. 자산 사양 이미지와 음료 주문 이미지는 `/uploads` 링크로 새 창에서 보기만 한다. SettingsPage 링크는 사이트 연결이다. 이 링크 및 업로드 이미지 미리보기용 Object URL은 다운로드 코드로 오인해 바꾸지 않았다.

## 2. 간헐적 먹통의 원인

코드에서 확인한 결함과 운영 재현 여부를 구분한다.

- 설치자료실은 서버 스트리밍을 프론트의 `response.blob()`이 전부 수신한 뒤에야 저장했다. 1GB 이상 파일도 동일했다. 다운로드 목록에 즉시 나타나지 않고 메모리/임시 저장 비용이 커지는 구조다.
- 목록/체크리스트/첨부파일/인사 양식 버튼에는 다운로드 준비 상태와 동기 중복 요청 잠금이 없었다.
- 모든 저장용 Object URL이 click 직후 해제되었다. 브라우저가 URL을 소비하기 전에 해제될 가능성이 있다. 운영 Chrome에서 이 경쟁 조건을 재현한 것은 아니다.
- PDF/이미지 미리보기는 비동기 요청 이후 window.open을 호출했다. 팝업 차단 시 반환값도 확인하지 않았다.
- 첨부 미리보기 헤더에 한글을 그대로 넣어 HTTP 헤더 인코딩 예외가 가능했다.
- 기존 requestBlob은 HTTP 오류는 검사했으나 성공 응답의 Content-Type 검증이 없었고, 헤더 수신 직후 타이머를 정리하여 본문 수신이 그 제한의 보호를 받지 못했다.
- CORS에서 Content-Disposition을 노출하지 않아 교차 출처에서 서버 파일명을 읽을 수 없었다.

다운로드 버튼의 type은 기존에도 button이었다. 설치자료실에서 loading=true가 고정되는 코드는 발견하지 못했다. 다운로드 콜백 연결은 코드에서 확인했다. overlay가 실제 클릭을 가로채는지, 운영 mixed content/CORS/프록시·worker timeout 여부는 브라우저 및 운영 서버 재현이 필요하다. API_BASE_URL은 현재 호스트 + 기존 8010을 쓰며 다운로드 경로 중복은 발견하지 못했다. 주소 및 서비스 설정은 변경하지 않았다.

## 3. 수정한 파일

- backend/app/services/download_service.py (신규 공통 준비/전송/실패 로그)
- backend/app/core/auth.py (다운로드 전용 인증 및 기존 사용자 상태 재검증)
- backend/app/main.py (공통 경로/미들웨어, 다운로드 응답 헤더 노출)
- backend/app/api/routers/install_files.py (파일명 헤더와 실패 로그 문맥)
- backend/app/api/routers/attachments.py (다운로드/미리보기 파일명 헤더와 로그 문맥)
- frontend/src/utils/downloadFile.js (신규 공통 다운로드)
- frontend/src/hooks/useDownloadStatus.js (신규 전역 준비 상태 구독)
- frontend/src/api/client.js (모든 다운로드/미리보기 호출 통일)
- frontend/src/App.jsx
- frontend/src/components/AssetExcelTools.jsx
- frontend/src/components/AttachmentPanel.jsx
- frontend/src/components/AuditLogTab.jsx
- frontend/src/components/HrAccountListPage.jsx
- frontend/src/components/InstallLibraryPage.jsx
- frontend/src/components/InstallLibraryList.jsx
- frontend/src/components/InstallChecklistPanel.jsx
- backend/tests/test_downloads.py (신규)
- frontend/tests/downloadFile.test.js (신규)
- docs/download-audit-2026-09-23.md (이 보고서)

## 4. 수정 내용

전체 다운로드를 네이티브 전송으로 전환했다. 클릭 즉시 메모리 Set으로 중복 준비를 막고 React 화면에 준비 상태를 공유한다. 공통 try/catch/finally로 숨겨진 form과 잠금을 정리한다. 기존 화면별 오류 영역을 유지한다. 인증 실패는 기존 로그인 해제 처리로 전달한다.

초기 구현에서 클릭 제스처 안에 열던 안내 창은 제거했다. 준비가 끝나면 현재 문서의 hidden iframe으로 숨겨진 form POST를 보내며, 현재 페이지와 탭 구성을 유지한다. 준비 단계 오류는 호출 화면에 표시한다. 준비 이후 401/403/404/서버 오류는 다운로드 ID가 일치하는 hidden iframe에서 `postMessage`로 부모 화면에 전달하고, API origin과 iframe window를 검증한 뒤 기존 오류 영역에 표시한다. 본문 전송 중 연결 단절은 서버 로그 및 브라우저 다운로드 목록에서 확인한다.

파일 응답은 ASCII filename fallback과 UTF-8 filename*를 제공한다. 기존 경로 정규화/저장 루트 제한을 유지하며 준비 및 실제 전송에서 파일 존재·읽기 가능 여부·권한을 확인한다. 서버 로그는 사용자 ID, 파일 ID, 파일명, UTC 요청 시각, API, HTTP 상태, 실패 유형을 기록한다. 인증 실패로 사용자를 확인할 수 없거나 메타데이터 조회 전 거부되면 해당 값은 null이다. 비밀번호/인증 헤더/전송 티켓/요청 본문을 기록하지 않는다. 본문 전송 중 예외는 로그 후 재발생시켜 잘린 파일을 정상 완료로 처리하지 않는다.

설치 다운로드 후 목록 조회 실패가 다운로드 자체의 실패처럼 보이는 결합도 제거했다. 카운터는 서버의 기존 실제 전송 처리에서 증가하며 목록 재조회 시 표시된다. 네이티브 전송 시작은 비동기이므로 현재 화면의 카운터가 즉시 갱신된다고 보장하지 않는다.

## 5. 공통 다운로드 처리 방식

1. 클릭 즉시 동일 작업 중복 잠금. 현재 화면에는 `준비 중…` 상태만 표시.
2. Bearer 인증으로 GET /downloads/prepare?path=...&query=... 요청.
3. 서버가 허용된 다운로드 경로, 기존 권한, 파일 상태를 검증하고 다운로드 전용 audience를 가진 서명 티켓 발급. 최대 90초이며 원래 로그인 만료 시각을 넘지 않는다.
4. 현재 문서의 고유 hidden iframe을 대상으로 숨겨진 form이 POST /downloads/transfer의 본문에 티켓과 서명된 다운로드 ID를 전달. URL·접근 로그에 티켓을 넣지 않는다.
5. 서버가 티켓 서명을 확인하고 허용된 기존 GET 다운로드 라우트로 내부 전달. 실제 사용자 활성 상태 및 메뉴 권한을 재검증한다. 원래 GET + Bearer API도 유지한다.
6. 파일은 FileResponse, Excel은 기존 StreamingResponse가 직접 전송. 파일명은 브라우저가 서버 헤더를 사용한다.
7. 프론트 준비 잠금은 전송 요청 인계 후 해제한다. 파일 완료 상태로 표시하지 않으며 전송 상태는 브라우저 목록에서 확인한다.

티켓은 특정 경로/검색 조건에만 유효하며 일반 API Bearer 인증에 사용할 수 없다. 메모리 내 세션 저장소를 추가하지 않아 다중 worker에서도 동일 서명 키로 검증 가능하다. 티켓은 유효기간 내 재사용 가능하다(일회성 티켓은 아님).

다운로드 Blob·Object URL 자체를 제거하여 Blob용 타입 확인/해제 타이밍 문제를 없앴다. setTimeout 기반 저장 지연이나 강제 새로고침은 추가하지 않았다. 기존 일반 API 요청의 연결 대기 제한은 유지했다.

## 6. 대용량 파일 처리 방식

파일 본문을 JS fetch/blob/arraybuffer로 수신하지 않는다. 브라우저 기본 다운로드가 서버 청크를 받으므로 React 메뉴 생명주기와 파일 수신이 분리된다. 서버 FileResponse를 유지하며 미들웨어는 ASGI 응답 청크를 버퍼링하지 않고 그대로 전달한다.

128MiB 및 1740MiB(약 1.7GiB) ZIP을 임시 생성했다. ASGI 청크 테스트와 별도의 실제 loopback HTTP POST 전송 테스트를 모두 수행했다. 테스트 서버는 실제 앱 DB/스케줄러를 사용하지 않는 격리 서버이며 OS 임의 포트를 사용한다(80/8080 제외). 테스트 후 종료하고 임시 파일을 정리한다. 실제 운영 NAS 원본의 무결성을 검증한 것은 아니다.

## 7. 테스트 결과

최종 결과: 프론트 빌드 성공, 프론트 전체 12개 테스트 통과, 백엔드 전체 256개 테스트 통과. 별도 대용량 옵션 실행에서는 신규 다운로드 테스트 11개가 통과했다(1740MiB 실제 HTTP 전송 포함). Vite 번들 크기 및 기존 Python 의존성 deprecation 경고는 남아 있으며 테스트 실패는 없다.

| 요청 테스트 | 결과 및 범위 |
| --- | --- |
| 소형 파일 | 서버 준비 → POST 전송, 원본 바이트 일치 통과 |
| 100MB 이상 | 128MiB ZIP의 ASGI 및 실제 HTTP 전송, 크기/해시 일치 통과 |
| 1GB 이상 | 1740MiB ZIP의 ASGI 및 실제 HTTP 전송, 크기/SHA-256 일치 통과 |
| 한글 / 공백 / 괄호 / 특수문자 | UTF-8 헤더 및 ASCII fallback 테스트 통과 |
| ZIP | 소형 ZIP/XLSX, 32MiB/1740MiB ZIP CRC 무결성 통과 |
| EXE / PDF | 테스트 바이트의 전송 및 한글 파일명 통과. 실제 EXE 실행이나 PDF 시각 렌더링은 미실시 |
| 없는 파일 | 준비 및 준비 이후 삭제된 파일 모두 404 통과 |
| 권한 없음 | 403, 준비 후 권한 변경도 실제 전송에서 거부 통과 |
| 빠른 연속 클릭 | 프론트 공통 유틸 mock 테스트에서 준비·form 전송 중복 방지 통과 |
| 메뉴 이동 후 재시도 | 모듈 전역 잠금·finally 복구 확인. 실제 UI 이동과 Chrome 진행 중 다운로드 유지는 미확인 |
| 로그인 만료 | 인증 없음/만료/잘못된 티켓/만료 티켓 401 통과 |
| 네트워크/서버 오류 | 프론트 오류 복구·재시도, 서버 전송 도중 예외 로그·전파 통과 |
| Excel 전체 | 자산 내보내기·양식, 감사로그, 인사계정 양식의 XLSX ZIP 구조 검증 통과 (DB 조회는 mock) |
| Chrome | 브라우저 도구 초기화 오류로 실브라우저 확인 미실시 |

큰 파일 테스트에서 수신 바이트를 누적 보관하지 않고 SHA-256만 갱신했으며 ASGI 단일 청크가 1MiB 이하임을 검사했다. 이는 브라우저 메모리 실측 결과가 아니다.

실행 명령:

```powershell
# frontend
npm run build
node --test tests/*.test.js
# backend
.venv/Scripts/python.exe -m unittest discover -s tests
$env:DOWNLOAD_LARGE_TESTS='1'
.venv/Scripts/python.exe -m unittest discover -s tests -p test_downloads.py
```

## 8. 남아있는 위험 요소

- 운영 NAS 파일·실제 Chrome UI·overlay·프록시 timeout·메모리 사용량 실측은 미검증이다. 브라우저 도구 초기화가 sandboxPolicy 누락 오류로 실패했다. 로컬 저장소 uploads에는 운영 1.7GB 원본이 없었다.
- 네이티브 다운로드는 웹페이지에 완료/중단 이벤트를 제공하지 않는다. 버튼은 준비 중 잠그고 인계 후 복구하며, 진행/실패/완료는 브라우저 다운로드 목록을 확인해야 한다. 인계 이후 새로 클릭하면 별도 다운로드가 시작될 수 있다.
- 다운로드는 팝업 권한을 사용하지 않는다. 첨부 PDF/이미지 미리보기는 현재 페이지 안의 모달에서만 열리며, 최대 20MB 첨부 제한 안에서만 Blob URL을 사용한다. 대용량 다운로드는 Blob을 사용하지 않는다.
- POST 네이티브 전송의 중단 지점 재개는 보장하지 않는다. 실패 후 버튼으로 재시도할 수 있다.
- 파일이 확인 이후 삭제되거나 저장소 연결이 전송 중 끊기면 실패할 수 있으며 로그에 남긴다. 이미 전송한 HTTP 헤더 상태는 도중에 변경할 수 없다.
- 기존 Excel 생성기의 서버 메모리 사용량, DB/프록시 운영 장애는 별도이다. 기존 DB 연결 실패의 503 상태는 유지하고 일반 서버 전송 예외는 500으로 처리한다.
- NAS/SCM/다른 서비스/배포 설정/포트는 변경하지 않았다. 운영 서비스 재시작·배포는 수행하지 않았다.
