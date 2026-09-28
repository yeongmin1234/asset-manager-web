import { MENU_ITEMS, MENU_ITEMS_BY_ID, MENU_PERMISSION_GROUPS } from "../config/menuDefinitions.js";

export { MENU_PERMISSION_GROUPS } from "../config/menuDefinitions.js";

export const MENU_PERMISSION_OPTIONS = MENU_PERMISSION_GROUPS.flatMap((group) =>
  group.items.map((item) => [item.permissionKey, item.permissionLabel || item.label]),
);

const MENU_PERMISSION_KEYS = new Set(MENU_PERMISSION_OPTIONS.map(([id]) => id));

const LEGACY_PERMISSION_MAP = {
  "beverage-orders": "drink_orders",
  "work-manuals": "work_manual",
  "vendor-contacts": "vendor_contacts",
  vehicles: "company_cars",
  "paju-fire-insurance": "fire_insurance",
  stats: "statistics",
  history: "changelog",
  "hr-list": "hr_list",
};

const SECTION_PERMISSION_MAP = Object.fromEntries(
  MENU_ITEMS.filter((item) => item.permissionKey).map((item) => [item.id, item.permissionKey]),
);

export function getPermissionForSection(sectionId) {
  return SECTION_PERMISSION_MAP[sectionId] || sectionId;
}

export function getAllowedSectionIds(menuPermissions = []) {
  const permissionSet = new Set(normalizeMenuPermissions(menuPermissions) || []);
  return Object.entries(SECTION_PERMISSION_MAP)
    .filter(([, permission]) => permissionSet.has(permission))
    .map(([sectionId]) => sectionId);
}

export function canAccessSection(sectionId, visibility, allowedSections, isAdmin) {
  const item = MENU_ITEMS_BY_ID[sectionId];
  return Boolean(
    item && visibility?.[item.menuKey] !== false &&
    (isAdmin || allowedSections?.has(sectionId)),
  );
}

export function normalizeMenuPermissions(values) {
  if (!Array.isArray(values)) return null;

  const normalized = [];
  const seen = new Set();
  values.forEach((value) => {
    if (typeof value !== "string") return;
    const rawKey = value.trim();
    const keys = rawKey === "network" ? ["access_info", "equipment_status"] : [LEGACY_PERMISSION_MAP[rawKey] || rawKey];
    keys.forEach((key) => {
      if (!MENU_PERMISSION_KEYS.has(key) || seen.has(key)) return;
      seen.add(key);
      normalized.push(key);
    });
  });
  return normalized;
}

export function haveSameMenuPermissions(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right)) return false;
  const leftSet = new Set(normalizeMenuPermissions(left));
  const rightSet = new Set(normalizeMenuPermissions(right));
  return leftSet.size === rightSet.size && [...leftSet].every((permission) => rightSet.has(permission));
}
