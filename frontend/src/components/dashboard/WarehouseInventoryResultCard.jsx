import React, { useMemo, useState } from "react";
import { formatInventoryDisplayQuantity, prepareWarehouseRows, WAREHOUSE_SORT_OPTIONS } from "../../utils/inventoryDisplayUtils.js";

function WarehouseInventoryResultCard({ result, onLoadMore }) {
  const [search, setSearch] = useState("");
  const [includeZero, setIncludeZero] = useState(false);
  const [sort, setSort] = useState("quantity_desc");
  const rows = useMemo(() => prepareWarehouseRows(
    (result.items || []).map((item) => ({ ...item, warehouse_name: item.item_name, warehouse_code: item.item_code })),
    { search, includeZero, sort },
  ), [result.items, search, includeZero, sort]);
  return (
    <article className="warehouse-location-result-card">
      <header><div><h4>{result.warehouse_name || result.warehouse_code}</h4><p>창고코드: {result.warehouse_code}</p></div>{result.cache_hit ? <small>최근 조회 결과</small> : null}</header>
      <div className="warehouse-location-summary"><span>총 품목 {result.summary?.item_count || 0}개</span><span>재고 보유 {result.summary?.positive_item_count || 0}개</span><span>0재고 {result.summary?.zero_item_count || 0}개</span>{result.summary?.negative_item_count ? <span>음수 {result.summary.negative_item_count}개</span> : null}</div>
      <div className="warehouse-location-controls"><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="품목명 또는 코드 검색" aria-label="창고 품목 검색" /><select value={sort} onChange={(event) => setSort(event.target.value)} aria-label="창고 품목 정렬">{WAREHOUSE_SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><label><input type="checkbox" checked={includeZero} onChange={(event) => setIncludeZero(event.target.checked)} />0재고 포함</label></div>
      <div className="warehouse-location-items">
        {rows.map((item) => <div key={item.item_code}><strong>{item.item_name || item.item_code}</strong><span>{[item.item_code, item.size].filter(Boolean).join(" · ")}</span><b className={String(item.quantity).startsWith("-") ? "negative" : ""}>{formatInventoryDisplayQuantity(item.quantity, item.unit)}</b></div>)}
        {!rows.length ? <p>표시할 품목 재고가 없습니다.</p> : null}
      </div>
      {result.items?.length < result.total ? <button type="button" className="inventory-outline-button warehouse-location-more" onClick={onLoadMore}>추가 조회</button> : null}
    </article>
  );
}

export default WarehouseInventoryResultCard;
