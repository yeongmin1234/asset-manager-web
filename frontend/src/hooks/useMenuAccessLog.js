import { useEffect } from "react";
import { recordMenuAccess } from "../api/client.js";


export const MENU_ACCESS_TARGETS = {
  users: { menu_key: "user_management", menu_name: "사용자 관리", route_path: "/admin/users" },
  "hr-list": { menu_key: "hr_list", menu_name: "인사업무 > 리스트", route_path: "/hr/list" },
  history: { menu_key: "history", menu_name: "변경 이력", route_path: "/history" },
  settings: { menu_key: "settings", menu_name: "설정", route_path: "/settings" },
  "work-manuals": { menu_key: "work_manual", menu_name: "업무설명서", route_path: "/work-manuals" },
  "install-library": { menu_key: "install_files", menu_name: "설치자료실", route_path: "/install-library" },
};

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
  useEffect(() => {
    const target = MENU_ACCESS_TARGETS[activeSection];
    if (!enabled || !target) return undefined;

    let active = true;
    recordMenuAccess(target).catch((error) => {
      if (active) console.error("메뉴 접근 기록 저장 실패", error);
    });
    return () => { active = false; };
  }, [activeSection, enabled]);
}
