import React, { useEffect, useMemo, useState } from "react";
import { getSidebarMenuLabels, updateSidebarMenuLabel } from "../api/client.js";
import { MENU_GROUPS, MENU_ITEMS } from "../config/menuDefinitions.js";
import { canAccessSection } from "../utils/menuPermissions.js";

export { MENU_ITEMS } from "../config/menuDefinitions.js";
const SIDEBAR_MENU_ORDER_STORAGE_KEY = "sidebar-menu-order-v1";

function PortalSidebar({
  activeSection = "dashboard",
  collapsed = false,
  menuVisibility = {},
  allowedMenuIds = null,
  isAdmin = false,
  onNavigate,
}) {
  const [menuOrder, setMenuOrder] = useState(() => getStoredMenuOrder());
  const [draftMenuOrder, setDraftMenuOrder] = useState(() => menuOrder);
  const [isEditingMenuOrder, setIsEditingMenuOrder] = useState(false);
  const [draggedMenuItem, setDraggedMenuItem] = useState(null);
  const [dragOverMenuItem, setDragOverMenuItem] = useState(null);
  const [menuLabels, setMenuLabels] = useState({});
  const [draftMenuLabels, setDraftMenuLabels] = useState({});
  const [menuEditError, setMenuEditError] = useState("");
  const [isSavingMenuLabels, setIsSavingMenuLabels] = useState(false);
  useEffect(() => {
    let active = true;
    getSidebarMenuLabels()
      .then((response) => { if (active) setMenuLabels(response?.labels || {}); })
      .catch(() => {});
    return () => { active = false; };
  }, []);
  const allowedSections = new Set(allowedMenuIds || []);
  const visibleMenuItems = MENU_ITEMS.filter((item) =>
    canAccessSection(item.id, menuVisibility, allowedSections, isAdmin),
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
    if (!isAdmin) return;
    setDraftMenuOrder(menuOrder);
    setDraftMenuLabels(menuLabels);
    setMenuEditError("");
    setIsEditingMenuOrder(true);
  };

  const handleSaveOrder = async () => {
    if (!isAdmin || isSavingMenuLabels) return;
    const changedItems = MENU_ITEMS.filter((item) => {
      const nextName = (draftMenuLabels[item.menuKey] ?? menuLabels[item.menuKey] ?? item.label).trim();
      const currentName = menuLabels[item.menuKey] ?? item.label;
      return nextName !== currentName;
    });
    const invalidItem = changedItems.find((item) => {
      const name = (draftMenuLabels[item.menuKey] || "").trim();
      return !name || name.length > 30 || /<[^>]*>|javascript\s*:|script/i.test(name);
    });
    if (invalidItem) {
      setMenuEditError("메뉴 이름은 HTML 없이 1~30자로 입력해주세요.");
      return;
    }
    setIsSavingMenuLabels(true);
    setMenuEditError("");
    try {
      let labels = menuLabels;
      for (const item of changedItems) {
        const response = await updateSidebarMenuLabel(item.menuKey, draftMenuLabels[item.menuKey].trim());
        labels = response?.labels || labels;
      }
      setMenuLabels(labels);
    } catch (error) {
      setMenuEditError(error?.message || "메뉴 이름을 저장하지 못했습니다.");
      setIsSavingMenuLabels(false);
      return;
    }
    const normalizedOrder = normalizeMenuOrder(draftMenuOrder);
    setMenuOrder(normalizedOrder);
    setDraftMenuOrder(normalizedOrder);
    saveMenuOrder(normalizedOrder);
    setIsEditingMenuOrder(false);
    setIsSavingMenuLabels(false);
  };

  const handleCancelOrder = () => {
    setDraftMenuOrder(menuOrder);
    setIsEditingMenuOrder(false);
    setDraggedMenuItem(null);
    setDragOverMenuItem(null);
  };

  const handleResetOrder = () => {
    const defaultOrder = getDefaultMenuOrder();
    setDraftMenuOrder(defaultOrder);
    setDraggedMenuItem(null);
    setDragOverMenuItem(null);
  };

  const handleDragStart = (event, groupTitle, itemId) => {
    setDraggedMenuItem({ groupTitle, itemId });
    setDragOverMenuItem(null);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", itemId);
  };

  const handleDragOver = (event, groupTitle, itemId) => {
    if (!draggedMenuItem || draggedMenuItem.groupTitle !== groupTitle) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";

    if (draggedMenuItem.itemId === itemId) {
      setDragOverMenuItem(null);
      return;
    }

    const targetRect = event.currentTarget.getBoundingClientRect();
    const position =
      event.clientY > targetRect.top + targetRect.height / 2 ? "after" : "before";
    setDragOverMenuItem({ groupTitle, itemId, position });
  };

  const handleDrop = (event, groupTitle, targetItemId) => {
    event.preventDefault();
    if (
      !draggedMenuItem ||
      draggedMenuItem.groupTitle !== groupTitle ||
      draggedMenuItem.itemId === targetItemId
    ) {
      setDraggedMenuItem(null);
      setDragOverMenuItem(null);
      return;
    }

    const insertPosition =
      dragOverMenuItem?.groupTitle === groupTitle &&
      dragOverMenuItem?.itemId === targetItemId
        ? dragOverMenuItem.position
        : "before";

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
      const nextGroupIds = reorderVisibleItem(
        currentGroupIds,
        visibleIds,
        draggedMenuItem.itemId,
        targetItemId,
        insertPosition,
      );
      return {
        ...currentOrder,
        [groupTitle]: nextGroupIds,
      };
    });
    setDraggedMenuItem(null);
    setDragOverMenuItem(null);
  };

  const handleDragEnd = () => {
    setDraggedMenuItem(null);
    setDragOverMenuItem(null);
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
          {isAdmin && !isEditingMenuOrder && (
            <button type="button" className="sidebar-edit-button" onClick={handleStartEdit}>
              편집
            </button>
          )}
        </div>
        {isAdmin && isEditingMenuOrder && (
          <div className="sidebar-edit-actions">
            <button type="button" className="sidebar-save-button" onClick={handleSaveOrder} disabled={isSavingMenuLabels}>
              {isSavingMenuLabels ? "저장 중" : "저장"}
            </button>
            <button type="button" className="sidebar-edit-button" onClick={handleResetOrder}>
              초기화
            </button>
            <button type="button" className="sidebar-edit-button" onClick={handleCancelOrder}>
              취소
            </button>
          </div>
        )}
        {isAdmin && menuEditError ? <p className="sidebar-edit-error">{menuEditError}</p> : null}
      </div>

      <nav className="portal-nav">
        {orderedMenuGroups.map((group) => {
          const groupItems = group.itemIds
            .map((itemId) => visibleMenuItemsById[itemId])
            .filter(Boolean);

          return (
            <div className="portal-nav-group" key={group.title}>
              <span className="portal-nav-group-title">{group.title}</span>
              <div className="portal-nav-group-items">
                {groupItems.map((item) => {
                  const itemClassName =
                    activeSection === item.id
                      ? "portal-nav-item sidebar-menu-item active"
                      : "portal-nav-item sidebar-menu-item";
                  const isDraggedItem =
                    draggedMenuItem?.groupTitle === group.title &&
                    draggedMenuItem?.itemId === item.id;
                  const dragOverPosition =
                    dragOverMenuItem?.groupTitle === group.title &&
                    dragOverMenuItem?.itemId === item.id
                      ? dragOverMenuItem.position
                      : null;
                  const editRowClassName = [
                    "sidebar-menu-edit-row",
                    isDraggedItem ? "is-dragging" : "",
                    dragOverPosition === "before" ? "is-drop-before" : "",
                    dragOverPosition === "after" ? "is-drop-after" : "",
                  ]
                    .filter(Boolean)
                    .join(" ");

                  if (isEditingMenuOrder) {
                    return (
                      <div
                        className={editRowClassName}
                        key={item.id}
                        draggable
                        onDragStart={(event) => handleDragStart(event, group.title, item.id)}
                        onDragOver={(event) => handleDragOver(event, group.title, item.id)}
                        onDrop={(event) => handleDrop(event, group.title, item.id)}
                        onDragEnd={handleDragEnd}
                      >
                        <button
                          type="button"
                          className={`${itemClassName} sidebar-menu-item-editing`}
                          onClick={(event) => event.preventDefault()}
                          aria-label={`${item.label} 메뉴 순서 편집`}
                        >
                          <span className="sidebar-drag-handle" aria-hidden="true">
                            ⋮⋮
                          </span>
                          <span aria-hidden="true">{item.icon}</span>
                          <input
                            className="sidebar-menu-label-input"
                            value={draftMenuLabels[item.menuKey] ?? menuLabels[item.menuKey] ?? item.label}
                            maxLength={30}
                            readOnly={item.id.startsWith("online-") || item.id === "scm-app"}
                            title={item.id === "scm-app" ? "SCM 시스템 메뉴 이름은 현재 고정되어 있습니다." : item.id.startsWith("online-") ? "온라인 TEAM 메뉴 이름은 현재 고정되어 있습니다." : undefined}
                            onChange={(event) => setDraftMenuLabels((current) => ({ ...current, [item.menuKey]: event.target.value }))}
                            onClick={(event) => event.stopPropagation()}
                            onKeyDown={(event) => event.stopPropagation()}
                            aria-label={`${item.label} 메뉴 이름`}
                          />
                        </button>
                      </div>
                    );
                  }

                  return (
                    <button
                      type="button"
                      key={item.id}
                      className={itemClassName}
                      aria-current={activeSection === item.id ? "page" : undefined}
                      onClick={() => onNavigate?.(item.id)}
                    >
                      <span aria-hidden="true">{item.icon}</span>
                      <strong>{menuLabels[item.menuKey] ?? item.label}</strong>
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

function reorderVisibleItem(groupIds, visibleIds, draggedId, targetId, position) {
  if (!visibleIds.includes(draggedId) || !visibleIds.includes(targetId)) {
    return groupIds;
  }

  if (draggedId === targetId) {
    return groupIds;
  }

  const nextGroupIds = groupIds.filter((id) => id !== draggedId);
  const targetIndex = nextGroupIds.indexOf(targetId);
  if (targetIndex < 0) {
    return groupIds;
  }

  const insertIndex = position === "after" ? targetIndex + 1 : targetIndex;
  return [
    ...nextGroupIds.slice(0, insertIndex),
    draggedId,
    ...nextGroupIds.slice(insertIndex),
  ];
}

export default PortalSidebar;
