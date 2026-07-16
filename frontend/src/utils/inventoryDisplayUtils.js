export const DEFAULT_WAREHOUSE_LIMIT = 5;

export const WAREHOUSE_SORT_OPTIONS = [
  { value: "quantity_desc", label: "재고 많은 순" },
  { value: "quantity_asc", label: "재고 적은 순" },
  { value: "name_asc", label: "창고명 가나다순" },
  { value: "name_desc", label: "창고명 역순" },
];

export function formatInventoryDisplayQuantity(value, unit = "") {
  const parsed = parseDecimal(value);
  if (!parsed) return value == null || value === "" ? "-" : String(value);
  const sign = parsed.negative && !isZeroDecimal(parsed) ? "-" : "";
  const grouped = parsed.whole.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",") || "0";
  const fraction = parsed.fraction.replace(/0+$/, "");
  const quantity = `${sign}${grouped}${fraction ? `.${fraction}` : ""}`;
  return unit ? `${quantity} ${unit}` : quantity;
}

export function compareInventoryQuantities(left, right) {
  const a = parseDecimal(left);
  const b = parseDecimal(right);
  if (!a && !b) return 0;
  if (!a) return 1;
  if (!b) return -1;
  if (a.negative !== b.negative) return a.negative ? -1 : 1;
  const direction = a.negative ? -1 : 1;
  const aWhole = a.whole.replace(/^0+/, "") || "0";
  const bWhole = b.whole.replace(/^0+/, "") || "0";
  if (aWhole.length !== bWhole.length) return (aWhole.length - bWhole.length) * direction;
  if (aWhole !== bWhole) return (aWhole > bWhole ? 1 : -1) * direction;
  const scale = Math.max(a.fraction.length, b.fraction.length);
  const af = a.fraction.padEnd(scale, "0");
  const bf = b.fraction.padEnd(scale, "0");
  return af === bf ? 0 : (af > bf ? 1 : -1) * direction;
}

export function prepareWarehouseRows(warehouses, { search = "", includeZero = false, sort = "quantity_desc" } = {}) {
  const query = normalizeWarehouseSearch(search);
  const rows = (Array.isArray(warehouses) ? warehouses : []).filter((warehouse) => {
    if (!warehouse || typeof warehouse !== "object") return false;
    if (!includeZero && compareInventoryQuantities(warehouse.quantity, 0) === 0) return false;
    return !query || normalizeWarehouseSearch(warehouse.warehouse_name || warehouse.warehouse_code).includes(query);
  });
  return [...rows].sort((a, b) => {
    if (sort === "quantity_asc") return compareInventoryQuantities(a.quantity, b.quantity);
    if (sort === "name_asc" || sort === "name_desc") {
      const compared = String(a.warehouse_name || a.warehouse_code || "").localeCompare(String(b.warehouse_name || b.warehouse_code || ""), "ko");
      return sort === "name_desc" ? -compared : compared;
    }
    return compareInventoryQuantities(b.quantity, a.quantity);
  });
}

export function summarizeWarehouses(warehouses) {
  const summary = { warehouse_count: 0, positive_warehouse_count: 0, zero_warehouse_count: 0, negative_warehouse_count: 0 };
  for (const warehouse of Array.isArray(warehouses) ? warehouses : []) {
    summary.warehouse_count += 1;
    const compared = compareInventoryQuantities(warehouse?.quantity, 0);
    if (compared > 0) summary.positive_warehouse_count += 1;
    else if (compared < 0) summary.negative_warehouse_count += 1;
    else summary.zero_warehouse_count += 1;
  }
  return summary;
}

export function inventoryQuantityStatus(value) {
  const compared = compareInventoryQuantities(value, 0);
  return compared < 0 ? "negative" : compared === 0 ? "zero" : "positive";
}

export function buildInventoryCardData({ inventoryResponse, context, responseData, intent, queriedAt } = {}) {
  const item = inventoryResponse?.items?.[0];
  if (!item) return null;
  const allWarehouses = Array.isArray(responseData?.all_warehouses)
    ? responseData.all_warehouses
    : Array.isArray(context?.inventory_result?.warehouses) ? context.inventory_result.warehouses : (item.warehouses || []);
  const isFiltered = responseData?.type === "inventory_warehouse_result"
    || ["inventory_warehouse_filter", "inventory_other_warehouses"].includes(intent);
  const totalQuantity = responseData?.total_quantity ?? context?.inventory_result?.total_quantity ?? item.total_quantity;
  return {
    item: { item_code: item.item_code, item_name: item.item_name, size: item.size, unit: item.unit },
    totalQuantity,
    displayedTotalQuantity: item.total_quantity,
    displayedWarehouses: Array.isArray(item.warehouses) ? item.warehouses : [],
    allWarehouses,
    filter: {
      is_filtered: isFiltered,
      warehouse_keyword: responseData?.warehouse_keyword || context?.last_warehouse_filter || null,
      label: intent === "inventory_other_warehouses" ? "나머지 창고" : null,
    },
    queriedAt: context?.searched_at || queriedAt || null,
    cache: responseData?.cache || null,
  };
}

function normalizeWarehouseSearch(value) {
  return String(value || "").trim().toLocaleLowerCase().replace(/\s+/g, "").normalize("NFC");
}

function parseDecimal(value) {
  const match = String(value ?? "").replace(/,/g, "").trim().match(/^([+-]?)(\d+)(?:\.(\d+))?$/);
  return match ? { negative: match[1] === "-", whole: match[2], fraction: match[3] || "" } : null;
}

function isZeroDecimal(value) {
  return /^0+$/.test(value.whole) && (!value.fraction || /^0+$/.test(value.fraction));
}
