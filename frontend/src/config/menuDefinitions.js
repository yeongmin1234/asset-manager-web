// The sidebar, global visibility settings, and user permission editor share these menu keys.
// A null permissionKey marks an existing administrator-only screen.
export const MENU_ITEMS = [
  { id: "dashboard", label: "대시보드", icon: "⌂", menuKey: "dashboard", permissionKey: "dashboard", routePath: "/dashboard", alwaysVisible: true },
  { id: "beverage-orders", label: "음료주문기록", icon: "▥", menuKey: "drink_orders", permissionKey: "drink_orders", routePath: "/beverage-orders", description: "음료 주문 기록 메뉴" },
  { id: "work-manuals", label: "업무설명서", icon: "▤", menuKey: "work_manual", permissionKey: "work_manual", routePath: "/work-manuals", description: "사내 업무설명서 메뉴" },
  { id: "vendor-contacts", label: "업체연락처", icon: "☎", menuKey: "vendor_contacts", permissionKey: "vendor_contacts", routePath: "/vendor-contacts", description: "업체 연락처 관리 메뉴" },
  { id: "expiration_schedules", label: "점검·만료 관리", icon: "!", menuKey: "expiration_schedules", permissionKey: "expiration_schedules", routePath: "/expiration-schedules", description: "점검 및 만료 일정 관리 메뉴" },
  { id: "assets", label: "자산 관리", icon: "▣", menuKey: "assets", permissionKey: "assets", routePath: "/assets", alwaysVisible: true },
  { id: "software", label: "SW 현황", icon: "▧", menuKey: "software", permissionKey: "software", routePath: "/software", description: "소프트웨어 라이선스 현황 메뉴" },
  { id: "vehicles", label: "법인차량 관리", icon: "▦", menuKey: "company_cars", permissionKey: "company_cars", routePath: "/vehicles", description: "법인차량과 보험 이력 관리 메뉴" },
  { id: "paju-fire-insurance", label: "파주화재보험", icon: "▨", menuKey: "fire_insurance", permissionKey: "fire_insurance", routePath: "/paju-fire-insurance", description: "파주 화재보험 계약 관리 메뉴" },
  { id: "access-info", label: "접속정보 관리", icon: "⌁", menuKey: "access_info", permissionKey: "access_info", routePath: "/access-info", description: "서버 및 시스템 접속정보 관리 메뉴" },
  { id: "equipment-status", label: "장비 현황", icon: "◌", menuKey: "equipment_status", permissionKey: "equipment_status", routePath: "/equipment-status", description: "네트워크 및 주요 장비 상태 메뉴" },
  { id: "excel", label: "엑셀 관리", icon: "▤", menuKey: "excel_management", permissionKey: null, routePath: "/excel", description: "엑셀 양식 다운로드와 일괄 등록 메뉴" },
  { id: "stats", label: "통계 / 리포트", icon: "▥", menuKey: "statistics", permissionKey: "statistics", routePath: "/statistics", description: "자산 통계와 리포트 메뉴" },
  { id: "history", label: "변경 이력", icon: "◷", menuKey: "history", permissionKey: "changelog", routePath: "/history", description: "자산 변경 이력 조회 메뉴" },
  { id: "install-library", label: "설치자료실", icon: "▩", menuKey: "install_files", permissionKey: null, routePath: "/install-library", description: "사내 설치 파일 자료실 메뉴" },
  { id: "hr-list", label: "리스트", accessLabel: "인사업무 > 리스트", permissionLabel: "인사업무 리스트", icon: "♙", menuKey: "hr_list", permissionKey: "hr_list", routePath: "/hr/list", description: "직원별 시스템 계정 현황 메뉴" },
  { id: "online-home", label: "온라인 TEAM 홈", icon: "⌂", menuKey: "online_home", permissionKey: "online_home", routePath: "/online", description: "온라인 업무 시작 화면" },
  { id: "online-recall", label: "리콜 관리", icon: "▤", menuKey: "online_recall", permissionKey: "online_recall", routePath: "/online/recall", description: "리콜 접수와 진행 현황 관리 메뉴" },
  { id: "online-order", label: "발주 관리", icon: "▤", menuKey: "online_order", permissionKey: "online_order", routePath: "/online/orders", description: "온라인 TEAM 발주 업무 관리 메뉴" },
  { id: "scm", label: "SCM", icon: "S", menuKey: "scm", permissionKey: null, routePath: "/scm", description: "SCM MariaDB 상태와 긴급 복구 준비 메뉴" },
  { id: "users", label: "사용자 관리", icon: "♙", menuKey: "user_management", permissionKey: null, routePath: "/admin/users", description: "사용자와 접속기록 관리 메뉴" },
  { id: "settings", label: "설정", icon: "⚙", menuKey: "settings", permissionKey: null, routePath: "/settings", alwaysVisible: true },
];

export const MENU_GROUPS = [
  { title: "업무", itemIds: ["dashboard", "beverage-orders", "work-manuals", "vendor-contacts", "expiration_schedules"] },
  { title: "자산", itemIds: ["assets", "install-library", "software", "vehicles", "excel", "stats", "history", "scm", "access-info", "equipment-status", "paju-fire-insurance"] },
  { title: "인사팀", itemIds: ["hr-list"] },
  { title: "온라인 TEAM", itemIds: ["online-home", "online-recall", "online-order"] },
  { title: "관리", itemIds: ["users", "settings"] },
];

export const MENU_ITEMS_BY_ID = Object.fromEntries(MENU_ITEMS.map((item) => [item.id, item]));
export const DEFAULT_MENU_VISIBILITY = Object.fromEntries(MENU_ITEMS.map((item) => [item.menuKey, true]));
export const MENU_VISIBILITY_GROUPS = MENU_GROUPS.map((group) => ({
  title: group.title,
  items: group.itemIds.map((id) => MENU_ITEMS_BY_ID[id]).filter((item) => !item.alwaysVisible),
})).filter((group) => group.items.length > 0);
export const MENU_PERMISSION_GROUPS = MENU_GROUPS.map((group) => ({
  title: group.title,
  items: group.itemIds.map((id) => MENU_ITEMS_BY_ID[id]).filter((item) => item.permissionKey),
})).filter((group) => group.items.length > 0);
export const ADMIN_ONLY_MENU_ITEMS = MENU_GROUPS.find((group) => group.title === "관리")
  .itemIds.map((id) => MENU_ITEMS_BY_ID[id]).filter((item) => !item.permissionKey);
