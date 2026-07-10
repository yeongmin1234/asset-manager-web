export const MENU_PERMISSION_OPTIONS = [
  ["dashboard", "대시보드"],
  ["drink_orders", "음료주문기록"],
  ["work_manual", "업무설명서"],
  ["vendor_contacts", "업체연락처"],
  ["expiration_schedules", "점검·만료 관리"],
  ["assets", "자산 관리"],
  ["software", "SW 현황"],
  ["company_cars", "법인차량 관리"],
  ["fire_insurance", "파주화재보험"],
  ["network", "네트워크 현황"],
  ["statistics", "통계 / 리포트"],
  ["changelog", "변경 이력"],
];

const MENU_PERMISSION_KEYS = new Set(MENU_PERMISSION_OPTIONS.map(([id]) => id));

const LEGACY_PERMISSION_MAP = {
  "beverage-orders": "drink_orders",
  "work-manuals": "work_manual",
  "vendor-contacts": "vendor_contacts",
  vehicles: "company_cars",
  "paju-fire-insurance": "fire_insurance",
  stats: "statistics",
  history: "changelog",
};

const SECTION_PERMISSION_MAP = {
  dashboard: "dashboard",
  "beverage-orders": "drink_orders",
  "work-manuals": "work_manual",
  "vendor-contacts": "vendor_contacts",
  expiration_schedules: "expiration_schedules",
  assets: "assets",
  software: "software",
  vehicles: "company_cars",
  "paju-fire-insurance": "fire_insurance",
  network: "network",
  stats: "statistics",
  history: "changelog",
};

export function getPermissionForSection(sectionId) {
  return SECTION_PERMISSION_MAP[sectionId] || sectionId;
}

export function getAllowedSectionIds(menuPermissions = []) {
  const permissionSet = new Set(normalizeMenuPermissions(menuPermissions) || []);
  return Object.entries(SECTION_PERMISSION_MAP)
    .filter(([, permission]) => permissionSet.has(permission))
    .map(([sectionId]) => sectionId);
}

export function normalizeMenuPermissions(values) {
  if (!Array.isArray(values)) return null;

  const normalized = [];
  const seen = new Set();
  values.forEach((value) => {
    if (typeof value !== "string") return;
    const key = LEGACY_PERMISSION_MAP[value.trim()] || value.trim();
    if (!MENU_PERMISSION_KEYS.has(key) || seen.has(key)) return;
    seen.add(key);
    normalized.push(key);
  });
  return normalized;
}

export function haveSameMenuPermissions(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right)) return false;
  const leftSet = new Set(normalizeMenuPermissions(left));
  const rightSet = new Set(normalizeMenuPermissions(right));
  return leftSet.size === rightSet.size && [...leftSet].every((permission) => rightSet.has(permission));
}
