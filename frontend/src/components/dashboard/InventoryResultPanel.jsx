import React, { useEffect, useState } from "react";

export function formatInventoryQuantity(value) {
  const raw = String(value ?? "").trim();
  if (!/^[+-]?\d+(?:\.\d+)?$/.test(raw)) return raw || "확인 필요";
  if (!raw.includes(".")) return raw.replace(/^\+/, "");
  const trimmed = raw.replace(/0+$/, "").replace(/\.$/, "").replace(/^\+/, "");
  return trimmed === "-0" ? "0" : trimmed;
}

function InventoryResultPanel({ state, isVisible = true }) {
  const [selectedCode, setSelectedCode] = useState(null);
  const items = Array.isArray(state.items) ? state.items : [];

  useEffect(() => {
    setSelectedCode(state.selectedItemCode || items[0]?.item_code || null);
  }, [items, state.selectedItemCode]);

  if (!isVisible) return null;
  const selectedItem = items.find((item) => item.item_code === selectedCode) || items[0] || null;

  return (
    <section className="dashboard-panel inventory-result-panel" aria-labelledby="inventory-result-title">
      <div className="dashboard-panel-heading">
        <div>
          <h3 id="inventory-result-title">재고 조회 결과</h3>
          {state.query ? <p className="inventory-result-query">검색: {state.query}</p> : null}
        </div>
        {state.searchedAt ? <span className="inventory-result-time">방금 조회</span> : null}
      </div>

      {state.analysis?.label ? (
        <div className="inventory-analysis-summary">
          <strong>{state.analysis.label}</strong>
          <span>일치 {items.length}건</span>
          {state.analysis.limited ? <em>최대 {state.analysis.scope_limit}개 범위</em> : null}
        </div>
      ) : null}

      {state.status === "idle" ? (
        <div className="dashboard-empty inventory-result-state">
          AI 업무 도우미에서 품목명 또는 품목코드를 조회하면 재고 결과가 이곳에 표시됩니다.
        </div>
      ) : null}
      {state.status === "loading" ? (
        <div className="inventory-result-state inventory-result-loading" role="status">
          <span aria-hidden="true" /> 이카운트 재고를 조회하고 있습니다.
        </div>
      ) : null}
      {state.status === "empty" ? (
        <div className="dashboard-empty inventory-result-state">검색 조건에 맞는 재고가 없습니다.</div>
      ) : null}
      {state.status === "error" ? (
        <div className="dashboard-empty inventory-result-state inventory-result-error">
          {state.errorMessage || "재고 정보를 불러오지 못했습니다. 잠시 후 다시 조회해 주세요."}
        </div>
      ) : null}

      {state.status === "success" && items.length > 0 ? (
        <>
          {items.length > 1 ? (
            <div className="inventory-result-table-wrap">
              <table className="inventory-result-table">
                <thead><tr>
                  {state.analysis?.type === "inventory_sort" ? <th>순위</th> : null}
                  <th>품목코드</th><th>품목명</th><th>단위</th><th>총 재고</th>
                  {state.analysis?.type === "inventory_compare" ? <th>차이</th> : null}
                  <th>창고 수</th>
                </tr></thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.item_code}
                      className={selectedItem?.item_code === item.item_code ? "selected" : ""}
                      onClick={() => setSelectedCode(item.item_code)}
                    >
                      {state.analysis?.type === "inventory_sort" ? <td>{item.rank || "-"}</td> : null}
                      <td>{item.item_code}</td><td>{item.item_name || "-"}</td><td>{item.unit || "-"}</td>
                      <td className={String(item.total_quantity).startsWith("-") ? "negative" : ""}>
                        {formatInventoryQuantity(item.total_quantity)}
                      </td>
                      {state.analysis?.type === "inventory_compare" ? <td>{formatInventoryQuantity(item.difference)}</td> : null}
                      <td>{item.warehouses?.length || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {selectedItem ? (
            <div className="inventory-result-detail">
              <dl>
                <div><dt>품목코드</dt><dd>{selectedItem.item_code}</dd></div>
                <div><dt>품목명</dt><dd>{selectedItem.item_name || "-"}</dd></div>
                <div><dt>단위</dt><dd>{selectedItem.unit || "-"}</dd></div>
                <div><dt>총 재고</dt><dd className={String(selectedItem.total_quantity).startsWith("-") ? "negative" : ""}>{formatInventoryQuantity(selectedItem.total_quantity)}</dd></div>
              </dl>
              <h4>창고별 재고</h4>
              {selectedItem.warehouses?.length ? (
                <ul>
                  {selectedItem.warehouses.map((warehouse, index) => (
                    <li key={`${warehouse.warehouse_code || "warehouse"}-${index}`}>
                      <span>{warehouse.warehouse_name || warehouse.warehouse_code || "창고"}</span>
                      <strong className={String(warehouse.quantity).startsWith("-") ? "negative" : ""}>{formatInventoryQuantity(warehouse.quantity)}</strong>
                    </li>
                  ))}
                </ul>
              ) : <p className="inventory-result-no-warehouse">등록된 창고별 재고가 없습니다.</p>}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

export default InventoryResultPanel;
