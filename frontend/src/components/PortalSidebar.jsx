import React from "react";

const MENU_ITEMS = [
  { id: "dashboard", label: "대시보드", icon: "⌂" },
  { id: "beverage-orders", label: "음료주문기록", icon: "▥" },
  { id: "assets", label: "자산 관리", icon: "▣" },
  { id: "software", label: "SW 현황", icon: "▧" },
  { id: "vehicles", label: "법인차량 관리", icon: "▦" },
  { id: "paju-fire-insurance", label: "파주화재보험", icon: "▨" },
  { id: "network", label: "네트워크 현황", icon: "◌" },
  { id: "excel", label: "엑셀 관리", icon: "▤" },
  { id: "stats", label: "통계 / 리포트", icon: "▥" },
  { id: "history", label: "변경 이력", icon: "◷" },
  { id: "scm", label: "SCM", icon: "S" },
  { id: "settings", label: "설정", icon: "⚙" },
];

const MENU_GROUPS = [
  {
    title: "업무",
    itemIds: ["dashboard", "beverage-orders"],
  },
  {
    title: "자산",
    itemIds: ["assets", "software", "vehicles", "paju-fire-insurance", "network"],
  },
  {
    title: "관리",
    itemIds: ["excel", "stats", "history", "scm", "settings"],
  },
];

function PortalSidebar({
  activeSection = "dashboard",
  collapsed = false,
  menuVisibility = {},
  onNavigate,
}) {
  const visibleMenuItems = MENU_ITEMS.filter(
    (item) => menuVisibility[item.id] !== false,
  );
  const visibleMenuItemsById = visibleMenuItems.reduce(
    (itemsById, item) => ({ ...itemsById, [item.id]: item }),
    {},
  );

  return (
    <aside className="portal-sidebar" aria-label="포털 메뉴" aria-hidden={collapsed}>
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
        {MENU_GROUPS.map((group) => {
          const groupItems = group.itemIds
            .map((itemId) => visibleMenuItemsById[itemId])
            .filter(Boolean);

          if (groupItems.length === 0) {
            return null;
          }

          return (
            <div className="portal-nav-group" key={group.title}>
              <span className="portal-nav-group-title">{group.title}</span>
              <div className="portal-nav-group-items">
                {groupItems.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    className={
                      activeSection === item.id
                        ? "portal-nav-item sidebar-menu-item active"
                        : "portal-nav-item sidebar-menu-item"
                    }
                    onClick={() => onNavigate?.(item.id)}
                  >
                    <span aria-hidden="true">{item.icon}</span>
                    <strong>{item.label}</strong>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
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
