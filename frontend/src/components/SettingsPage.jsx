import React, { useMemo, useState } from "react";

const SETTINGS_SECTIONS = [
  {
    id: "access",
    label: "접속 정보",
    description: "Frontend, Backend, Health, 서버/포트, DB, 경로, 배포, 백업 정보",
    icon: "A",
  },
  { id: "menu-visibility", label: "메뉴 표시 설정", description: "사이드바 표시 메뉴", icon: "M" },
  { id: "admin", label: "관리자 설정", description: "보호 메뉴와 인증 상태", icon: "P" },
  { id: "handover", label: "인수인계", description: "담당자 변경 시 확인", icon: "H" },
  { id: "caution", label: "주의사항", description: "절대 금지 항목", icon: "X" },
];

const MENU_VISIBILITY_ITEMS = [
  {
    id: "excel",
    label: "엑셀 관리",
    description: "엑셀 양식 다운로드와 일괄 등록 메뉴",
  },
  {
    id: "stats",
    label: "통계 / 리포트",
    description: "자산 통계와 리포트 메뉴",
  },
  {
    id: "history",
    label: "변경 이력",
    description: "자산 변경 이력 조회 메뉴",
  },
  {
    id: "network",
    label: "네트워크 현황",
    description: "네트워크 장비 상태 메뉴",
  },
  {
    id: "paju-fire-insurance",
    label: "파주화재보험",
    description: "파주 화재보험 계약 관리 메뉴",
  },
];

const PROTECTED_MENU_ITEMS = [
  {
    id: "software",
    label: "SW 현황",
    description: "소프트웨어 라이선스 현황 메뉴",
  },
  {
    id: "vehicles",
    label: "법인차량 관리",
    description: "법인차량과 보험 이력 관리 메뉴",
  },
  {
    id: "paju-fire-insurance",
    label: "파주화재보험",
    description: "파주 화재보험 계약 관리 메뉴",
  },
  {
    id: "beverage-orders",
    label: "음료주문기록",
    description: "음료 주문 기록 조회/관리 메뉴",
  },
  {
    id: "network",
    label: "네트워크 현황",
    description: "네트워크 장비 상태 메뉴",
  },
  {
    id: "history",
    label: "변경 이력",
    description: "자산 변경 이력 조회 메뉴",
  },
  {
    id: "settings",
    label: "설정",
    description: "운영 설정 화면. 기본값은 보호 OFF 권장",
  },
];

const ACCESS_TABS = [
  { id: "basic", label: "기본 접속" },
  { id: "ports", label: "서버/포트" },
  { id: "database", label: "DB 정보" },
  { id: "paths", label: "경로" },
  { id: "deploy", label: "배포" },
  { id: "backup", label: "백업/운영" },
];

function SettingsCard({ title, description, children, important = false }) {
  return (
    <section className={important ? "settings-card settings-card-important" : "settings-card"}>
      <div className="settings-card-heading">
        <div>
          <h4>{title}</h4>
          {description ? <p>{description}</p> : null}
        </div>
      </div>
      <div className="settings-card-body">{children}</div>
    </section>
  );
}

function InfoList({ items }) {
  return (
    <dl className="settings-info-list settings-info-list-readable">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.href ? <a href={item.href}>{item.value}</a> : item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RuleList({ rules }) {
  return (
    <ul className="settings-rule-list">
      {rules.map((rule) => (
        <li key={rule}>{rule}</li>
      ))}
    </ul>
  );
}

function SettingsPage({
  adminAuthClearedAt = null,
  menuVisibility = {},
  onClearAdminAuth,
  onMenuVisibilityChange,
  onProtectedMenuChange,
  protectedMenus = {},
}) {
  const [activeSettingsSection, setActiveSettingsSection] = useState("access");
  const [activeAccessTab, setActiveAccessTab] = useState("basic");

  const activeSection = useMemo(
    () =>
      SETTINGS_SECTIONS.find((section) => section.id === activeSettingsSection) ||
      SETTINGS_SECTIONS[0],
    [activeSettingsSection],
  );

  const renderDetail = () => {
    switch (activeSettingsSection) {
      case "menu-visibility":
        return (
          <SettingsCard
            title="메뉴 표시 설정"
            description="사이드바에 표시할 메뉴를 선택합니다. 숨김 처리해도 기능은 삭제되지 않습니다."
          >
            <div className="settings-menu-visibility-list">
              {MENU_VISIBILITY_ITEMS.map((item) => {
                const isVisible = menuVisibility[item.id] !== false;

                return (
                  <label className="settings-menu-toggle" key={item.id}>
                    <span className="settings-menu-toggle-text">
                      <strong>{item.label}</strong>
                      <small>{item.description}</small>
                    </span>
                    <span className="settings-menu-toggle-control">
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={(event) =>
                          onMenuVisibilityChange?.(item.id, event.target.checked)
                        }
                      />
                      <span className="settings-menu-toggle-switch" aria-hidden="true" />
                    </span>
                  </label>
                );
              })}
            </div>
            <p className="settings-muted">
              대시보드, 자산 관리, 설정 메뉴는 항상 표시됩니다.
            </p>
          </SettingsCard>
        );
      case "admin":
        return (
          <div className="settings-tab-card-stack">
            <SettingsCard
              title="보호 메뉴 설정"
              description="선택한 메뉴는 진입 시 관리자 비밀번호 확인이 필요합니다."
            >
              <div className="settings-menu-visibility-list">
                {PROTECTED_MENU_ITEMS.map((item) => {
                  const isProtected = protectedMenus[item.id] === true;

                  return (
                    <label className="settings-menu-toggle" key={item.id}>
                      <span className="settings-menu-toggle-text">
                        <strong>{item.label}</strong>
                        <small>{item.description}</small>
                      </span>
                      <span className="settings-menu-toggle-control">
                        <input
                          type="checkbox"
                          checked={isProtected}
                          onChange={(event) =>
                            onProtectedMenuChange?.(item.id, event.target.checked)
                          }
                        />
                        <span className="settings-menu-toggle-switch" aria-hidden="true" />
                      </span>
                    </label>
                  );
                })}
              </div>
              <p className="settings-muted">
                대시보드와 자산 관리는 보호 대상에서 제외했습니다. 설정 메뉴 보호는 접근 차단 위험이 있어 기본 OFF를 권장합니다.
              </p>
            </SettingsCard>

            <SettingsCard
              title="관리자 인증"
              description="관리자 비밀번호는 backend/.env에서만 관리합니다."
              important
            >
              <RuleList
                rules={[
                  "보호 메뉴 ON/OFF 설정은 브라우저 localStorage에 저장됩니다.",
                  "관리자 인증 성공 시 token과 만료 시간만 sessionStorage에 저장됩니다.",
                  "비밀번호는 프론트엔드 코드, localStorage, sessionStorage에 저장하지 않습니다.",
                  "기본 인증 유지 시간은 backend 설정 기준이며 기본값은 60분입니다.",
                ]}
              />
              <div className="settings-admin-actions">
                <button type="button" className="secondary-button" onClick={onClearAdminAuth}>
                  관리자 인증 해제
                </button>
              </div>
              {adminAuthClearedAt && (
                <p className="settings-muted">현재 브라우저 탭의 관리자 인증을 해제했습니다.</p>
              )}
            </SettingsCard>
          </div>
        );
      case "access":
        return (
          <div className="settings-access-panel">
            <div className="settings-access-tabs" role="tablist" aria-label="접속 정보 세부 탭">
              {ACCESS_TABS.map((tab) => (
                <button
                  className={`settings-access-tab ${activeAccessTab === tab.id ? "active" : ""}`}
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeAccessTab === tab.id}
                  onClick={() => setActiveAccessTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="settings-access-content">
              <div className="settings-tab-content">{renderAccessTab()}</div>
            </div>
          </div>
        );
      case "handover":
        return (
          <SettingsCard title="인수인계 메모" description="담당자 변경 시 가장 먼저 확인할 정보입니다." important>
            <InfoList
              items={[
                { label: "앱 접속 주소", value: "http://192.168.222.210:3010", href: "http://192.168.222.210:3010/" },
                { label: "NAS 프로젝트 경로", value: "/volume6/총무/서버/자산관리 프로젝트/asset-manager-web" },
                { label: "DB 컨테이너", value: "asset-postgres" },
                { label: "DB 데이터 폴더", value: "/volume6/총무/서버/자산관리 프로젝트/postgres-data" },
                { label: "DB 백업", value: "deploy/backup_db.sh 기준으로 관리" },
                { label: "서비스 점검", value: "deploy/health_check.sh로 확인" },
                { label: "금지 사항", value: "80/8080 포트와 기존 SCM 서버는 절대 변경하지 않음" },
              ]}
            />
          </SettingsCard>
        );
      case "caution":
      default:
        return (
          <SettingsCard title="주의사항" description="민감정보와 기존 NAS 서비스 보호를 위한 운영 원칙입니다." important>
            <RuleList
              rules={[
                "기존 서버/SCM/기존 NAS 서비스 건드리지 않기",
                "80/8080 포트 사용 또는 변경 금지",
                ".env 파일 Git 업로드 금지",
                "PostgreSQL 데이터 폴더 직접 삭제 금지",
                "DB 비밀번호, GitHub token 등 민감정보 화면 표시 금지",
              ]}
            />
          </SettingsCard>
        );
    }
  };

  const renderAccessTab = () => {
    switch (activeAccessTab) {
      case "ports":
        return (
          <SettingsCard title="서버/포트" description="80, 8080 포트는 기존 서비스 보호를 위해 사용하지 않습니다.">
            <InfoList
              items={[
                { label: "Frontend Port", value: "3010" },
                { label: "Backend Port", value: "8010" },
                { label: "PostgreSQL Host Port", value: "15432" },
                { label: "PostgreSQL Container Port", value: "5432" },
                { label: "사용 금지 포트", value: "80, 8080" },
              ]}
            />
          </SettingsCard>
        );
      case "database":
        return (
          <div className="settings-tab-card-stack">
            <SettingsCard title="DB 정보" description="비밀번호와 DATABASE_URL 전체 문자열은 표시하지 않습니다." important>
              <InfoList
                items={[
                  { label: "DB 종류", value: "PostgreSQL" },
                  { label: "Container Name", value: "asset-postgres" },
                  { label: "DB Name", value: "asset_manager_prod" },
                  { label: "DB User", value: "asset_user" },
                  { label: "DB Host", value: "127.0.0.1" },
                  { label: "DB Port", value: "15432" },
                  { label: "Container 내부 Port", value: "5432" },
                  { label: "PostgreSQL 데이터 폴더", value: "/volume6/총무/서버/자산관리 프로젝트/postgres-data" },
                ]}
              />
            </SettingsCard>

            <SettingsCard title="DB 주의사항" description="장애 대응 전 반드시 확인할 항목입니다." important>
              <RuleList
                rules={[
                  "PostgreSQL 데이터 폴더는 직접 삭제/수정하지 말 것",
                  "운영 DB 직접 삭제/초기화 금지",
                  "DB 비밀번호는 backend/.env에서만 관리하며 화면에는 표시하지 않음",
                  "DB 비밀번호에 @가 포함될 경우 DATABASE_URL에서는 %40으로 URL 인코딩 필요",
                  ".env, DATABASE_URL, password, token 출력 금지",
                  "DB 접속 문제 발생 시 먼저 DB Health URL을 확인",
                  "DB 복구/백업 작업 전에는 반드시 백업 파일 존재 여부를 확인",
                ]}
              />
            </SettingsCard>
          </div>
        );
      case "paths":
        return (
          <SettingsCard title="경로 정보" description="운영/개발 파일 위치입니다. .env 내용은 표시하지 않습니다.">
            <InfoList
              items={[
                { label: "PC 개발 경로", value: "C:\\Users\\박종윤\\Desktop\\asset-manager-web" },
                { label: "NAS 운영 경로", value: "/volume6/총무/서버/자산관리 프로젝트/asset-manager-web" },
                { label: "Backend env 위치", value: "backend/.env" },
                { label: "Frontend env 위치", value: "frontend/.env" },
                { label: "Deploy env 위치", value: "deploy/.env" },
                { label: "Upload Directory", value: "../uploads" },
                { label: "Export Directory", value: "../exports" },
              ]}
            />
          </SettingsCard>
        );
      case "deploy":
        return (
          <SettingsCard title="배포 정보" description="NAS 운영 반영 시 기준 흐름입니다.">
            <RuleList
              rules={[
                "개발 흐름: PC/Codex 수정 → GitHub push → NAS git pull",
                "NAS 반영 명령: cd \"/volume6/총무/서버/자산관리 프로젝트/asset-manager-web\"",
                "NAS 반영 명령: deploy/deploy.sh",
                "NAS에서는 되도록 직접 코드 수정하지 않음",
                "Frontend 변경 후 npm run build 필요",
                "Backend 변경 후 backend 재시작 필요",
                "DB migration 변경 시 backend에서 alembic upgrade head 필요",
                ".env 파일 Git 업로드 금지",
              ]}
            />
          </SettingsCard>
        );
      case "backup":
        return (
          <SettingsCard title="백업/운영" description="백업 위치는 스크립트 내용을 기준으로 확인합니다.">
            <InfoList
              items={[
                { label: "DB 백업 스크립트", value: "deploy/backup_db.sh" },
                { label: "Health Check", value: "deploy/health_check.sh" },
                { label: "로그 로테이션", value: "deploy/rotate_logs.sh" },
                { label: "백업 보관 기준", value: "30일" },
                { label: "백업 위치 확인", value: "deploy/backup_db.sh 내용을 기준으로 확인" },
              ]}
            />
          </SettingsCard>
        );
      case "basic":
      default:
        return (
          <div className="settings-tab-card-stack">
            <SettingsCard title="기본 접속 정보" description="운영 화면과 상태 점검 URL입니다.">
              <InfoList
                items={[
                  { label: "Frontend URL", value: "http://192.168.222.210:3010", href: "http://192.168.222.210:3010/" },
                  { label: "Backend API URL", value: "http://192.168.222.210:8010", href: "http://192.168.222.210:8010/" },
                  { label: "Backend Health", value: "http://127.0.0.1:8010/health", href: "http://127.0.0.1:8010/health" },
                  { label: "DB Health", value: "http://127.0.0.1:8010/health/db", href: "http://127.0.0.1:8010/health/db" },
                ]}
              />
            </SettingsCard>

            <SettingsCard title="운영 기준" description="읽기 전용 운영 기준 정보입니다.">
              <InfoList
                items={[
                  { label: "시스템명", value: "사내 자산관리 시스템" },
                  { label: "회사명", value: "The Limo &" },
                  { label: "관리 부서", value: "총무팀" },
                  { label: "운영 방식", value: "NAS 직접 실행" },
                  { label: "운영 범위", value: "회사 내부망 전용" },
                ]}
              />
              <p className="settings-muted">이 설정 화면은 저장 기능이 없는 읽기 전용 인수인계 정보입니다.</p>
            </SettingsCard>
          </div>
        );
    }
  };

  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <div className="settings-hero">
        <div>
          <span className="section-kicker">Operations Settings</span>
          <h2 id="settings-title">설정</h2>
          <p>운영 정보와 메뉴 표시, 보호 메뉴 기준을 관리합니다.</p>
        </div>
        <span className="settings-version-badge">운영 설정</span>
      </div>

      <div className="settings-layout">
        <aside className="settings-side-nav" aria-label="설정 목록">
          {SETTINGS_SECTIONS.map((section) => (
            <button
              className={`settings-nav-item ${activeSettingsSection === section.id ? "active" : ""}`}
              key={section.id}
              type="button"
              onClick={() => setActiveSettingsSection(section.id)}
            >
              <span className="settings-nav-icon" aria-hidden="true">
                {section.icon}
              </span>
              <span>
                <strong>{section.label}</strong>
                <small>{section.description}</small>
              </span>
            </button>
          ))}
        </aside>

        <div className="settings-detail-panel">
          <div className="settings-detail-heading">
            <div>
              <h3>{activeSection.label}</h3>
              <p>{activeSection.description}</p>
            </div>
          </div>
          <div className="settings-detail-content">{renderDetail()}</div>
        </div>
      </div>
    </section>
  );
}

export default SettingsPage;
