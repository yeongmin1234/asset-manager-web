import React, { useMemo, useRef, useState } from "react";
import { DEFAULT_WAREHOUSE_LIMIT, formatInventoryDisplayQuantity, inventoryQuantityStatus, prepareWarehouseRows, summarizeWarehouses } from "../../utils/inventoryDisplayUtils.js";
import WarehouseInventoryList from "./WarehouseInventoryList.jsx";
import WarehouseInventoryModal from "./WarehouseInventoryModal.jsx";

function formatQueriedAt(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function InventoryAnswerCard({ data, onClearFilter }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [includeZero, setIncludeZero] = useState(false);
  const openButtonRef = useRef(null);
  const sourceWarehouses = data.filter?.is_filtered ? data.displayedWarehouses : data.allWarehouses;
  const rows = useMemo(() => prepareWarehouseRows(sourceWarehouses, { includeZero, sort: "quantity_desc" }), [sourceWarehouses, includeZero]);
  const visibleRows = rows.slice(0, DEFAULT_WAREHOUSE_LIMIT);
  const summary = summarizeWarehouses(data.allWarehouses);
  const displayTotal = data.filter?.is_filtered ? data.displayedTotalQuantity : data.totalQuantity;
  const totalStatus = inventoryQuantityStatus(displayTotal);
  const item = data.item || {};
  return (
    <article className="inventory-answer-card">
      <header className="inventory-answer-header">
        <div><h4>{item.item_name || item.item_code || "품목 정보"}</h4><p>{[item.item_code && `품목코드: ${item.item_code}`, item.size && `규격: ${item.size}`, item.unit && `단위: ${item.unit}`].filter(Boolean).join(" · ")}</p></div>
        {formatQueriedAt(data.queriedAt) ? <time dateTime={data.queriedAt}>조회 {formatQueriedAt(data.queriedAt)}</time> : null}
      </header>
      {data.filter?.is_filtered ? <div className="inventory-answer-filter"><strong>필터: {data.filter.label || data.filter.warehouse_keyword || "창고"}</strong><span>일치 창고 {data.displayedWarehouses.length}개</span></div> : null}
      <div className={`inventory-answer-total inventory-answer-total-${totalStatus}`}><span>{data.filter?.is_filtered ? "필터 합계" : "총재고"}</span><strong>{formatInventoryDisplayQuantity(displayTotal, item.unit)}</strong>{totalStatus === "zero" ? <small>재고 없음</small> : totalStatus === "negative" ? <small>음수 재고</small> : null}</div>
      {data.filter?.is_filtered ? <p className="inventory-answer-original-total">전체 총재고 {formatInventoryDisplayQuantity(data.totalQuantity, item.unit)}</p> : null}
      <div className="inventory-answer-summary"><span>전체 창고 {summary.warehouse_count}</span><span>양수 {summary.positive_warehouse_count}</span><span>0재고 {summary.zero_warehouse_count}</span><span>음수 {summary.negative_warehouse_count}</span></div>
      <WarehouseInventoryList warehouses={visibleRows} unit={item.unit} />
      {!rows.length && !includeZero && summary.zero_warehouse_count ? <p className="inventory-answer-zero-hidden">현재 0재고 창고가 숨겨져 있습니다.</p> : null}
      <div className="inventory-answer-actions">
        <button ref={openButtonRef} type="button" className="inventory-outline-button" onClick={() => setIsModalOpen(true)}>전체 창고 {data.allWarehouses.length}개 보기</button>
        <button type="button" className="inventory-outline-button" onClick={() => setIncludeZero((current) => !current)}>{includeZero ? "0재고 제외" : "0재고 포함"}</button>
        {data.filter?.is_filtered ? <button type="button" className="inventory-outline-button" onClick={() => onClearFilter?.(data)}>필터 해제</button> : null}
      </div>
      {data.cache?.is_cached ? <small className="inventory-answer-cache">최근 조회 결과</small> : null}
      <WarehouseInventoryModal isOpen={isModalOpen} item={item} totalQuantity={data.totalQuantity} warehouses={data.allWarehouses} onClose={() => setIsModalOpen(false)} returnFocusRef={openButtonRef} />
    </article>
  );
}

export default InventoryAnswerCard;
