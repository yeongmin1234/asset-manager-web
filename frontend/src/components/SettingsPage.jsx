import React, { useMemo, useState } from "react";
import { MENU_VISIBILITY_GROUPS } from "../config/menuDefinitions.js";

const SETTINGS_SECTIONS = [
  { id: "overview", label: "운영 기준", description: "시스템과 관리 범위", icon: "O" },
  { id: "menu-visibility", label: "메뉴 표시 설정", description: "사이드바 표시 메뉴", icon: "M" },
  { id: "admin", label: "관리자 설정", description: "보호 메뉴와 인증 상태", icon: "P" },
  { id: "handover", label: "인수인계", description: "담당자 변경 시 확인", icon: "H" },
  { id: "caution", label: "주의사항", description: "절대 금지 항목", icon: "X" },
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
  { id: "access-info", label: "접속정보 관리", description: "서버 및 시스템 접속정보 관리 메뉴" },
  { id: "equipment-status", label: "장비 현황", description: "네트워크 및 주요 장비 상태 메뉴" },
  {
    id: "history",
    label: "변경 이력",
    description: "자산 변경 이력 조회 메뉴",
  },
  {
    id: "install-library",
    label: "설치자료실",
    description: "설치자료 등록/수정/삭제는 별도 관리자 인증이 필요합니다.",
  },
  {
    id: "scm",
    label: "SCM",
    description: "SCM 서버 운영 관리 메뉴. 기본값은 보호 ON 권장",
  },
  {
    id: "settings",
    label: "설정",
    description: "운영 설정 화면. 기본값은 보호 OFF 권장",
  },
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
  adminResetSuccessMessage = "",
  adminStatus = { configured: false, error: "", isLoading: true },
  menuVisibility = {},
  menuVisibilityError = "",
  onAdminPasswordSave,
  onAdminPasswordResetRequest,
  onClearAdminAuth,
  onMenuVisibilityChange,
  onProtectedMenuChange,
  protectedMenus = {},
}) {
  const [activeSettingsSection, setActiveSettingsSection] = useState("overview");
  const [adminPasswordForm, setAdminPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [adminPasswordState, setAdminPasswordState] = useState({
    error: "",
    isSubmitting: false,
    message: "",
  });

  const activeSection = useMemo(
    () =>
      SETTINGS_SECTIONS.find((section) => section.id === activeSettingsSection) ||
      SETTINGS_SECTIONS[0],
    [activeSettingsSection],
  );
  const isAdminConfigured = adminStatus.configured === true;

  const handleAdminPasswordFieldChange = (field, value) => {
    setAdminPasswordForm((current) => ({
      ...current,
      [field]: value,
    }));
    setAdminPasswordState((current) => ({
      ...current,
      error: "",
      message: "",
    }));
  };

  const handleAdminPasswordSubmit = async (event) => {
    event.preventDefault();
    const newPassword = adminPasswordForm.newPassword;
    if (newPassword.length < 6) {
      setAdminPasswordState({ error: "관리자 비밀번호는 6자 이상이어야 합니다.", isSubmitting: false, message: "" });
      return;
    }
    if (newPassword !== adminPasswordForm.confirmPassword) {
      setAdminPasswordState({ error: "새 비밀번호와 확인값이 일치하지 않습니다.", isSubmitting: false, message: "" });
      return;
    }
    if (isAdminConfigured && !adminPasswordForm.currentPassword) {
      setAdminPasswordState({ error: "현재 비밀번호를 입력해주세요.", isSubmitting: false, message: "" });
      return;
    }

    setAdminPasswordState({ error: "", isSubmitting: true, message: "" });
    try {
      await onAdminPasswordSave?.({
        current_password: isAdminConfigured ? adminPasswordForm.currentPassword : "",
        new_password: newPassword,
      });
      setAdminPasswordForm({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
      setAdminPasswordState({
        error: "",
        isSubmitting: false,
        message: isAdminConfigured
          ? "관리자 비밀번호가 변경되었습니다."
          : "관리자 비밀번호가 설정되었습니다.",
      });
    } catch (error) {
      setAdminPasswordState({
        error: error.message,
        isSubmitting: false,
        message: "",
      });
    }
  };

  const renderDetail = () => {
    switch (activeSettingsSection) {
      case "menu-visibility":
        return (
          <SettingsCard
            title="메뉴 표시 설정"
            description="사이드바에 표시할 메뉴를 선택합니다. 숨김 처리해도 기능은 삭제되지 않습니다."
          >
            <div className="settings-menu-visibility-groups">
              {MENU_VISIBILITY_GROUPS.map((group) => (
                <section className="settings-menu-visibility-group" key={group.title} aria-label={`${group.title} 메뉴 표시`}>
                  <h3>{group.title}</h3>
                  <div className="settings-menu-visibility-list">
                    {group.items.map((item) => {
                      const isVisible = menuVisibility[item.menuKey] !== false;
                      return (
                        <label className="settings-menu-toggle" key={item.id}>
                          <span className="settings-menu-toggle-text">
                            <strong>{item.permissionLabel || item.label}</strong>
                            <small>{item.description}</small>
                          </span>
                          <span className="settings-menu-toggle-control">
                            <input
                              type="checkbox"
                              checked={isVisible}
                              onChange={(event) => {
                                Promise.resolve(onMenuVisibilityChange?.(item.menuKey, event.target.checked)).catch(() => {});
                              }}
                            />
                            <span className="settings-menu-toggle-switch" aria-hidden="true" />
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
            {menuVisibilityError ? <p className="settings-inline-error">{menuVisibilityError}</p> : null}
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
              description={
                isAdminConfigured
                  ? "선택한 메뉴는 진입 시 관리자 비밀번호 확인이 필요합니다."
                  : "관리자 비밀번호 설정 전에는 보호 메뉴 기능이 비활성화됩니다."
              }
            >
              {!isAdminConfigured && (
                <div className="settings-admin-disabled-notice">
                  <strong>관리자 비밀번호가 설정되지 않아 보호 메뉴 기능이 비활성화되어 있습니다.</strong>
                  <span>아래 관리자 비밀번호를 설정하면 보호 메뉴 기능을 사용할 수 있습니다.</span>
                  {adminStatus.error && <small>상태 확인 실패: {adminStatus.error}</small>}
                </div>
              )}
              <div className="settings-menu-visibility-list">
                {PROTECTED_MENU_ITEMS.map((item) => {
                  const isProtected = protectedMenus[item.id] === true;

                  return (
                    <label
                      className={
                        isAdminConfigured
                          ? "settings-menu-toggle"
                          : "settings-menu-toggle settings-menu-toggle-disabled"
                      }
                      key={item.id}
                    >
                      <span className="settings-menu-toggle-text">
                        <strong>{item.label}</strong>
                        <small>{item.description}</small>
                      </span>
                      <span className="settings-menu-toggle-control">
                        <input
                          type="checkbox"
                          checked={isProtected}
                          disabled={!isAdminConfigured}
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
                {isAdminConfigured
                  ? "대시보드와 자산 관리는 보호 대상에서 제외했습니다. 설정 메뉴 보호는 접근 차단 위험이 있어 기본 OFF를 권장합니다."
                  : "저장된 보호 ON 값이 있어도 관리자 비밀번호가 설정되기 전에는 실제 보호가 적용되지 않습니다."}
              </p>
            </SettingsCard>

            <SettingsCard
              title="관리자 비밀번호"
              description="비밀번호 원문은 저장하지 않고 백엔드에서 해시로 저장합니다."
              important
            >
              <div className={isAdminConfigured ? "settings-admin-status configured" : "settings-admin-status"}>
                <strong>{isAdminConfigured ? "설정됨" : "미설정"}</strong>
                <span>
                  {isAdminConfigured
                    ? "보호 메뉴 기능을 사용할 수 있습니다."
                    : "관리자 비밀번호가 아직 설정되지 않았습니다. 비밀번호를 설정하면 보호 메뉴 기능을 사용할 수 있습니다."}
                </span>
              </div>
              <form className="settings-admin-password-form" onSubmit={handleAdminPasswordSubmit}>
                {isAdminConfigured && (
                  <label className="field">
                    <span>현재 비밀번호</span>
                    <input
                      type="password"
                      value={adminPasswordForm.currentPassword}
                      autoComplete="current-password"
                      disabled={adminPasswordState.isSubmitting}
                      onChange={(event) => handleAdminPasswordFieldChange("currentPassword", event.target.value)}
                    />
                  </label>
                )}
                <label className="field">
                  <span>새 비밀번호</span>
                  <input
                    type="password"
                    value={adminPasswordForm.newPassword}
                    autoComplete="new-password"
                    disabled={adminPasswordState.isSubmitting}
                    onChange={(event) => handleAdminPasswordFieldChange("newPassword", event.target.value)}
                  />
                </label>
                <label className="field">
                  <span>새 비밀번호 확인</span>
                  <input
                    type="password"
                    value={adminPasswordForm.confirmPassword}
                    autoComplete="new-password"
                    disabled={adminPasswordState.isSubmitting}
                    onChange={(event) => handleAdminPasswordFieldChange("confirmPassword", event.target.value)}
                  />
                </label>
                {adminPasswordState.error && (
                  <p className="settings-admin-form-error">{adminPasswordState.error}</p>
                )}
                {adminPasswordState.message && (
                  <p className="settings-admin-form-message">{adminPasswordState.message}</p>
                )}
                {adminResetSuccessMessage && (
                  <p className="settings-admin-form-message">{adminResetSuccessMessage}</p>
                )}
                <div className="settings-admin-actions">
                  <button type="submit" disabled={adminPasswordState.isSubmitting}>
                    {isAdminConfigured ? "변경" : "저장"}
                  </button>
                </div>
              </form>
              <div className="settings-admin-reset-section">
                <div>
                  <strong>관리자 비밀번호 초기화</strong>
                  <p>현재 관리자 비밀번호를 잊은 경우 초기화 코드를 사용해 새 비밀번호로 재설정할 수 있습니다.</p>
                </div>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={onAdminPasswordResetRequest}
                  disabled={adminPasswordState.isSubmitting}
                >
                  관리자 비밀번호 초기화
                </button>
              </div>
              <RuleList
                rules={[
                  "보호 메뉴 ON/OFF 설정은 브라우저 localStorage에 저장됩니다.",
                  "관리자 인증 성공 시 token과 만료 시간만 sessionStorage에 저장됩니다.",
                  "비밀번호는 프론트엔드 코드, localStorage, sessionStorage에 저장하지 않습니다.",
                  "DB에는 PBKDF2 해시만 저장하며 비밀번호 원문은 저장하지 않습니다.",
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
      case "overview":
        return (
          <SettingsCard title="운영 기준" description="시스템 관리 범위입니다.">
            <InfoList
              items={[
                { label: "시스템명", value: "사내 자산관리 시스템" },
                { label: "회사명", value: "The Limo &" },
                { label: "관리 부서", value: "총무팀" },
                { label: "운영 방식", value: "사내 운영" },
                { label: "운영 범위", value: "회사 내부망 전용" },
              ]}
            />
          </SettingsCard>
        );
      case "handover":
        return (
          <SettingsCard title="인수인계 메모" description="담당자 변경 시 확인할 업무 기준입니다." important>
            <RuleList
              rules={[
                "담당 부서와 메뉴별 관리 책임자를 확인합니다.",
                "변경 예정 사항과 미완료 작업을 기록합니다.",
                "장애나 문의가 발생하면 담당 관리자에게 전달합니다.",
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
                "운영 환경의 설정 변경은 담당자와 먼저 확인",
                ".env 파일 Git 업로드 금지",
                "데이터 삭제 전 복구 가능 여부 확인",
                "DB 비밀번호, GitHub token 등 민감정보 화면 표시 금지",
              ]}
            />
          </SettingsCard>
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
