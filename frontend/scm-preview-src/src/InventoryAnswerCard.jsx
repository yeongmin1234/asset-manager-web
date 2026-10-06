import React, { useMemo, useState } from "react";
import { formatQuantity, sortWarehouses } from "./inventoryDisplayUtils";
import WarehouseInventoryList from "./WarehouseInventoryList";
import WarehouseInventoryModal from "./WarehouseInventoryModal";
export default function InventoryAnswerCard({ data }) {
  const [showZero, setShowZero] = useState(false), [sort, setSort] = useState("quantity-desc"), [search, setSearch] = useState(""), [all, setAll] = useState(false);
  const filtered = useMemo(() => sortWarehouses((data.warehouses || []).filter((row) => (showZero || row.quantity !== 0) && (!search || row.warehouse_name.toLowerCase().includes(search.toLowerCase()))), sort), [data.warehouses, showZero, sort, search]);
  const visible = filtered.slice(0, 5);
  return <article className="ai-inventory-card"><header><b>데이터 기준: 이카운트</b><span>{data.cache_hit ? "캐시" : "최신 조회"}{data.stale ? " · 이전 데이터" : ""}</span></header>
    <dl><div><dt>품목명</dt><dd>{data.item?.item_name}</dd></div><div><dt>품목코드</dt><dd>{data.item?.item_code}</dd></div><div><dt>규격</dt><dd>{data.item?.specification || "-"}</dd></div><div><dt>단위</dt><dd>{data.item?.unit || "-"}</dd></div><div><dt>총재고</dt><dd>{formatQuantity(data.total_quantity)} {data.item?.unit || ""}</dd></div><div><dt>조회 시각</dt><dd>{data.queried_at ? new Date(data.queried_at).toLocaleString() : "-"}</dd></div></dl>
    <div className="ai-inventory-tools"><input placeholder="창고 검색" value={search} onChange={(e) => setSearch(e.target.value)} /><select value={sort} onChange={(e) => setSort(e.target.value)}><option value="quantity-desc">재고 많은 순</option><option value="quantity-asc">재고 적은 순</option><option value="name-asc">창고명 가나다순</option><option value="name-desc">창고명 역순</option></select><label><input type="checkbox" checked={showZero} onChange={(e) => setShowZero(e.target.checked)} />0재고 포함</label></div>
    <WarehouseInventoryList rows={visible} unit={data.item?.unit} />
    {filtered.length > 5 && <button type="button" className="ai-show-all" onClick={() => setAll(true)}>전체 창고 보기 ({filtered.length})</button>}
    {all && <WarehouseInventoryModal rows={filtered} unit={data.item?.unit} onClose={() => setAll(false)} />}
  </article>;
}
