import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { formatInventoryDisplayQuantity, prepareWarehouseRows, WAREHOUSE_SORT_OPTIONS } from "../../utils/inventoryDisplayUtils.js";
import WarehouseInventoryList from "./WarehouseInventoryList.jsx";

function WarehouseInventoryModal({ isOpen, item, totalQuantity, warehouses, onClose, returnFocusRef }) {
  const [search, setSearch] = useState("");
  const [includeZero, setIncludeZero] = useState(false);
  const [sort, setSort] = useState("quantity_desc");
  const searchRef = useRef(null);
  const closeRef = useRef(null);
  const rows = useMemo(() => prepareWarehouseRows(warehouses, { search, includeZero, sort }), [warehouses, search, includeZero, sort]);

  useEffect(() => {
    if (!isOpen) return undefined;
    setSearch(""); setIncludeZero(false); setSort("quantity_desc");
    const timer = window.setTimeout(() => searchRef.current?.focus(), 0);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const focusable = [searchRef.current, closeRef.current].filter(Boolean);
        if (!focusable.length) return;
        const first = focusable[0]; const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.clearTimeout(timer); window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef?.current?.focus();
    };
  }, [isOpen, onClose, returnFocusRef]);
  if (!isOpen) return null;

  return createPortal(
    <div className="warehouse-inventory-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="warehouse-inventory-modal" role="dialog" aria-modal="true" aria-labelledby="warehouse-inventory-title">
        <header>
          <div><h3 id="warehouse-inventory-title">{item.item_name || item.item_code || "품목"} 창고별 재고</h3><p>총재고 {formatInventoryDisplayQuantity(totalQuantity, item.unit)}</p></div>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="창고별 재고 닫기">닫기</button>
        </header>
        <div className="warehouse-inventory-controls">
          <label><span>창고 검색</span><input ref={searchRef} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="창고명 검색" /></label>
          <label><span>정렬</span><select value={sort} onChange={(event) => setSort(event.target.value)}>{WAREHOUSE_SORT_OPTIONS.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></label>
          <label className="warehouse-zero-toggle"><input type="checkbox" checked={includeZero} onChange={(event) => setIncludeZero(event.target.checked)} />0재고 포함</label>
        </div>
        <div className="warehouse-inventory-count">표시 {rows.length}개 / 전체 {warehouses.length}개</div>
        <div className="warehouse-inventory-scroll">
          <WarehouseInventoryList warehouses={rows} unit={item.unit} />
          {!rows.length && !includeZero && warehouses.some((row) => String(row.quantity) === "0") ? <button type="button" className="inventory-outline-button" onClick={() => setIncludeZero(true)}>0재고 포함</button> : null}
        </div>
      </section>
    </div>, document.body,
  );
}

export default WarehouseInventoryModal;
