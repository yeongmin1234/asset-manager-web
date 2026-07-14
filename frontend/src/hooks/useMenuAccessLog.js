import { useEffect, useRef } from "react";
import { recordMenuAccess } from "../api/client.js";
import { MENU_ITEMS } from "../components/PortalSidebar.jsx";


export const MENU_ACCESS_TARGETS = Object.fromEntries(MENU_ITEMS.map((item) => [item.id, {
  menu_key: item.menuKey,
  menu_name: item.accessLabel || item.label,
  route_path: item.routePath,
}]));

export const HR_EXCEL_IMPORT_TARGET = {
  menu_key: "excel_import", menu_name: "엑셀 일괄등록", route_path: "/hr/list",
};

export function recordMenuAccessBestEffort(target) {
  return recordMenuAccess(target).catch((error) => {
    console.error("메뉴 접근 기록 저장 실패", error);
    return null;
  });
}


export default function useMenuAccessLog(activeSection, enabled = true) {
  const lastRecordedSection = useRef("");
  useEffect(() => {
    const target = MENU_ACCESS_TARGETS[activeSection];
    if (!enabled || !target || lastRecordedSection.current === activeSection) return undefined;
    lastRecordedSection.current = activeSection;

    let active = true;
    recordMenuAccess(target).catch((error) => {
      if (active) console.error("메뉴 접근 기록 저장 실패", error);
    });
    return () => { active = false; };
  }, [activeSection, enabled]);
}
