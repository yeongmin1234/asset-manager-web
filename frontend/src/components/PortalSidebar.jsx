import React, { useMemo, useState } from "react";

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
  { id: "install-library", label: "설치자료실", icon: "▩" },
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
    itemIds: ["excel", "stats", "history", "install-library", "scm", "settings"],
  },
];
const SIDEBAR_MENU_ORDER_STORAGE_KEY = "sidebar-menu-order-v1";

function PortalSidebar({
  activeSection = "dashboard",
  collapsed = false,
  menuVisibility = {},
  onNavigate,
}) {
  const [menuOrder, setMenuOrder] = useState(() => getStoredMenuOrder());
  const [draftMenuOrder, setDraftMenuOrder] = useState(() => menuOrder);
  const [isEditingMenuOrder, setIsEditingMenuOrder] = useState(false);
  const visibleMenuItems = MENU_ITEMS.filter(
    (item) => menuVisibility[item.id] !== false,
  );
  const visibleMenuItemsById = visibleMenuItems.reduce(
    (itemsById, item) => ({ ...itemsById, [item.id]: item }),
    {},
  );
  const activeMenuOrder = isEditingMenuOrder ? draftMenuOrder : menuOrder;
  const orderedMenuGroups = useMemo(
    () => applyMenuOrder(MENU_GROUPS, activeMenuOrder),
    [activeMenuOrder],
  );

  const handleStartEdit = () => {
    setDraftMenuOrder(menuOrder);
    setIsEditingMenuOrder(true);
  };

  const handleSaveOrder = () => {
    const normalizedOrder = normalizeMenuOrder(draftMenuOrder);
    setMenuOrder(normalizedOrder);
    setDraftMenuOrder(normalizedOrder);
    saveMenuOrder(normalizedOrder);
    setIsEditingMenuOrder(false);
  };

  const handleCancelOrder = () => {
    setDraftMenuOrder(menuOrder);
    setIsEditingMenuOrder(false);
  };

  const handleResetOrder = () => {
    const defaultOrder = getDefaultMenuOrder();
    setDraftMenuOrder(defaultOrder);
  };

  const handleMoveMenuItem = (groupTitle, itemId, direction) => {
    setDraftMenuOrder((currentOrder) => {
      const group = MENU_GROUPS.find((candidate) => candidate.title === groupTitle);
      if (!group) {
        return currentOrder;
      }
      const currentGroupIds = normalizeGroupOrder(
        currentOrder[groupTitle],
        group.itemIds,
      );
      const visibleIds = currentGroupIds.filter((id) => visibleMenuItemsById[id]);
      const nextGroupIds = moveVisibleItem(currentGroupIds, visibleIds, itemId, direction);
      return {
        ...currentOrder,
        [groupTitle]: nextGroupIds,
      };
    });
  };

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

      <div className={isEditingMenuOrder ? "sidebar-edit-panel editing" : "sidebar-edit-panel"}>
        <div className="sidebar-edit-heading">
          <span>{isEditingMenuOrder ? "메뉴 편집 중" : "사이드바 메뉴"}</span>
          {!isEditingMenuOrder && (
            <button type="button" className="sidebar-edit-button" onClick={handleStartEdit}>
              편집
            </button>
          )}
        </div>
        {isEditingMenuOrder && (
          <div className="sidebar-edit-actions">
            <button type="button" className="sidebar-save-button" onClick={handleSaveOrder}>
              저장
            </button>
            <button type="button" className="sidebar-edit-button" onClick={handleResetOrder}>
              초기화
            </button>
            <button type="button" className="sidebar-edit-button" onClick={handleCancelOrder}>
              취소
            </button>
          </div>
        )}
      </div>

      <nav className="portal-nav">
        {orderedMenuGroups.map((group) => {
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
                {groupItems.map((item, itemIndex) => {
                  const itemClassName =
                    activeSection === item.id
                      ? "portal-nav-item sidebar-menu-item active"
                      : "portal-nav-item sidebar-menu-item";

                  if (isEditingMenuOrder) {
                    return (
                      <div className="sidebar-menu-edit-row" key={item.id}>
                        <button
                          type="button"
                          className={`${itemClassName} sidebar-menu-item-editing`}
                          onClick={(event) => event.preventDefault()}
                        >
                          <span aria-hidden="true">{item.icon}</span>
                          <strong>{item.label}</strong>
                        </button>
                        <div className="sidebar-move-controls" aria-label={`${item.label} 순서 변경`}>
                          <button
                            type="button"
                            className="sidebar-move-button"
                            disabled={itemIndex === 0}
                            onClick={() => handleMoveMenuItem(group.title, item.id, "up")}
                            aria-label={`${item.label} 위로 이동`}
                          >
                            ↑
                          </button>
                          <button
                            type="button"
                            className="sidebar-move-button"
                            disabled={itemIndex === groupItems.length - 1}
                            onClick={() => handleMoveMenuItem(group.title, item.id, "down")}
                            aria-label={`${item.label} 아래로 이동`}
                          >
                            ↓
                          </button>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <button
                      type="button"
                      key={item.id}
                      className={itemClassName}
                      onClick={() => onNavigate?.(item.id)}
                    >
                      <span aria-hidden="true">{item.icon}</span>
                      <strong>{item.label}</strong>
                    </button>
                  );
                })}
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

function getDefaultMenuOrder() {
  return MENU_GROUPS.reduce(
    (order, group) => ({
      ...order,
      [group.title]: [...group.itemIds],
    }),
    {},
  );
}

function getStoredMenuOrder() {
  if (typeof window === "undefined") {
    return getDefaultMenuOrder();
  }

  try {
    const storedValue = window.localStorage.getItem(SIDEBAR_MENU_ORDER_STORAGE_KEY);
    if (!storedValue) {
      return getDefaultMenuOrder();
    }
    return normalizeMenuOrder(JSON.parse(storedValue));
  } catch {
    return getDefaultMenuOrder();
  }
}

function saveMenuOrder(order) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(
      SIDEBAR_MENU_ORDER_STORAGE_KEY,
      JSON.stringify(normalizeMenuOrder(order)),
    );
  } catch {
    // Ignore storage failures; the edited order still applies during this session.
  }
}

function normalizeMenuOrder(order) {
  return MENU_GROUPS.reduce(
    (normalizedOrder, group) => ({
      ...normalizedOrder,
      [group.title]: normalizeGroupOrder(order?.[group.title], group.itemIds),
    }),
    {},
  );
}

function normalizeGroupOrder(storedIds, defaultIds) {
  const safeStoredIds = Array.isArray(storedIds) ? storedIds : [];
  const knownStoredIds = safeStoredIds.filter((id) => defaultIds.includes(id));
  const missingDefaultIds = defaultIds.filter((id) => !knownStoredIds.includes(id));
  return [...knownStoredIds, ...missingDefaultIds];
}

function applyMenuOrder(groups, order) {
  const normalizedOrder = normalizeMenuOrder(order);
  return groups.map((group) => ({
    ...group,
    itemIds: normalizedOrder[group.title],
  }));
}

function moveVisibleItem(groupIds, visibleIds, itemId, direction) {
  const currentVisibleIndex = visibleIds.indexOf(itemId);
  if (currentVisibleIndex < 0) {
    return groupIds;
  }
  const targetVisibleIndex =
    direction === "up" ? currentVisibleIndex - 1 : currentVisibleIndex + 1;
  if (targetVisibleIndex < 0 || targetVisibleIndex >= visibleIds.length) {
    return groupIds;
  }

  const targetId = visibleIds[targetVisibleIndex];
  const nextGroupIds = groupIds.filter((id) => id !== itemId);
  const targetIndex = nextGroupIds.indexOf(targetId);
  const insertIndex = direction === "up" ? targetIndex : targetIndex + 1;
  return [
    ...nextGroupIds.slice(0, insertIndex),
    itemId,
    ...nextGroupIds.slice(insertIndex),
  ];
}

export default PortalSidebar;
