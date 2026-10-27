import React from "react";
import { formatQuantity } from "./inventoryDisplayUtils";
export default function WarehouseInventoryList({ rows, unit }) {
  return <table className="ai-inventory-table"><thead><tr><th>창고</th><th>창고코드</th><th>재고</th></tr></thead>
    <tbody>{rows.map((row) => <tr key={`${row.warehouse_code}-${row.warehouse_name}`}><td>{row.warehouse_name}</td><td>{row.warehouse_code}</td><td>{formatQuantity(row.quantity)} {unit || ""}</td></tr>)}</tbody>
  </table>;
}
