import React from "react";
import { formatInventoryDisplayQuantity, inventoryQuantityStatus } from "../../utils/inventoryDisplayUtils.js";

function WarehouseInventoryList({ warehouses, unit }) {
  if (!warehouses.length) return <p className="inventory-answer-empty">표시할 창고 재고가 없습니다.</p>;
  return (
    <ul className="inventory-answer-warehouse-list">
      {warehouses.map((warehouse, index) => {
        const status = inventoryQuantityStatus(warehouse.quantity);
        return (
          <li key={`${warehouse.warehouse_code || warehouse.warehouse_name || "warehouse"}-${index}`}>
            <span title={warehouse.warehouse_name || warehouse.warehouse_code || "창고"}>{warehouse.warehouse_name || warehouse.warehouse_code || "창고"}</span>
            <strong className={`inventory-quantity-${status}`}>{formatInventoryDisplayQuantity(warehouse.quantity, unit)}</strong>
            <small>{status === "negative" ? "음수 재고" : status === "zero" ? "재고 없음" : "정상"}</small>
          </li>
        );
      })}
    </ul>
  );
}

export default WarehouseInventoryList;
