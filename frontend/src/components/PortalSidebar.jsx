import React from "react";

const MENU_ITEMS = [
  { id: "dashboard", label: "대시보드", icon: "⌂" },
  { id: "assets", label: "자산 관리", icon: "▣" },
  { id: "software", label: "SW 현황", icon: "▧" },
  { id: "vehicles", label: "법인차량 관리", icon: "▦" },
  { id: "excel", label: "엑셀 관리", icon: "▤" },
  { id: "stats", label: "통계 / 리포트", icon: "▥" },
  { id: "history", label: "변경 이력", icon: "◷" },
  { id: "settings", label: "설정", icon: "⚙" },
];

function PortalSidebar({ activeSection = "dashboard", onNavigate }) {
  return (
    <aside className="portal-sidebar" aria-label="포털 메뉴">
      <div className="portal-brand">
        <button
          type="button"
          className="portal-brand-button"
          onClick={() => onNavigate?.("dashboard")}
          aria-label="대시보드로 이동"
        >
          <img className="portal-brand-logo" src="/logo.png" alt="ASSET MANAGER 사내 자산관리 시스템" />
        </button>
      </div>

      <nav className="portal-nav">
        {MENU_ITEMS.map((item) => (
          <button
            type="button"
            key={item.id}
            className={activeSection === item.id ? "portal-nav-item active" : "portal-nav-item"}
            onClick={() => onNavigate?.(item.id)}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="portal-help-card">
        <strong>시스템 문의</strong>
        <span>총무팀 전산 담당자</span>
        <span>02-710-4143</span>
        <span>yeong00o@limotech.co.kr</span>
      </div>
    </aside>
  );
}

export default PortalSidebar;
