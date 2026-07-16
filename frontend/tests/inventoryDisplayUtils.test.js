import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_WAREHOUSE_LIMIT,
  buildInventoryCardData,
  compareInventoryQuantities,
  formatInventoryDisplayQuantity,
  prepareWarehouseRows,
  summarizeWarehouses,
} from "../src/utils/inventoryDisplayUtils.js";

const warehouses = [
  { warehouse_name: "파주창고", quantity: "92" },
  { warehouse_name: "본사창고", quantity: "67.00" },
  { warehouse_name: "파주RMA", quantity: "5.5" },
  { warehouse_name: "제로창고", quantity: "0" },
  { warehouse_name: "음수창고", quantity: "-7" },
  { warehouse_name: "기타창고", quantity: "2" },
];

test("formats integer, decimal, negative, unit and invalid values safely", () => {
  assert.equal(formatInventoryDisplayQuantity("1234.00", "EA"), "1,234 EA");
  assert.equal(formatInventoryDisplayQuantity("2.500", "BOX"), "2.5 BOX");
  assert.equal(formatInventoryDisplayQuantity("-7", "EA"), "-7 EA");
  assert.equal(formatInventoryDisplayQuantity(null), "-");
});

test("default warehouse view excludes zero, preserves negative and supports top five", () => {
  const rows = prepareWarehouseRows(warehouses);
  assert.equal(rows.some((row) => row.quantity === "0"), false);
  assert.equal(rows.some((row) => row.quantity === "-7"), true);
  assert.equal(rows.slice(0, DEFAULT_WAREHOUSE_LIMIT).length, 5);
});

test("warehouse search ignores spaces and case", () => {
  assert.deepEqual(prepareWarehouseRows(warehouses, { search: "파 주" }).map((row) => row.warehouse_name), ["파주창고", "파주RMA"]);
});

test("supports all four sort modes with decimal numeric comparison", () => {
  assert.equal(prepareWarehouseRows(warehouses, { includeZero: true, sort: "quantity_desc" })[0].quantity, "92");
  assert.equal(prepareWarehouseRows(warehouses, { includeZero: true, sort: "quantity_asc" })[0].quantity, "-7");
  assert.equal(prepareWarehouseRows(warehouses, { includeZero: true, sort: "name_asc" })[0].warehouse_name, "기타창고");
  assert.equal(prepareWarehouseRows(warehouses, { includeZero: true, sort: "name_desc" }).at(-1).warehouse_name, "기타창고");
  assert.equal(compareInventoryQuantities("10.01", "9.999"), 1);
});

test("summarizes positive, zero and negative warehouses", () => {
  assert.deepEqual(summarizeWarehouses(warehouses), {
    warehouse_count: 6, positive_warehouse_count: 4, zero_warehouse_count: 1, negative_warehouse_count: 1,
  });
});

test("filtered card preserves displayed and full warehouse results separately", () => {
  const data = buildInventoryCardData({
    inventoryResponse: { items: [{ item_code: "1", item_name: "랜턴", unit: "EA", total_quantity: "97.5", warehouses: warehouses.slice(0, 3) }] },
    context: { searched_at: "2026-07-16T12:34:00+09:00", last_warehouse_filter: "파주", inventory_result: { total_quantity: "159.5", warehouses } },
    responseData: { type: "inventory_warehouse_result", warehouse_keyword: "파주", total_quantity: "159.5", all_warehouses: warehouses },
    intent: "inventory_item_warehouse_search",
  });
  assert.equal(data.filter.is_filtered, true);
  assert.equal(data.displayedWarehouses.length, 3);
  assert.equal(data.allWarehouses.length, 6);
  assert.equal(data.totalQuantity, "159.5");
});
