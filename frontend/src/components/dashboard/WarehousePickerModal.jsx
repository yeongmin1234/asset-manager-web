import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getInventoryWarehouses } from "../../api/client.js";

const RECENT_KEY = "assetManager.recentInventoryWarehouses";

function readRecent() {
  try { const value = JSON.parse(window.localStorage.getItem(RECENT_KEY) || "[]"); return Array.isArray(value) ? value.slice(0, 5) : []; } catch { return []; }
}

function WarehousePickerModal({ isOpen, onClose, onSelect }) {
  const [keyword, setKeyword] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const searchRef = useRef(null);
  const openerRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    openerRef.current = document.activeElement;
    setKeyword(""); setRecent(readRecent()); setActiveIndex(-1);
    const timer = window.setTimeout(() => searchRef.current?.focus(), 0);
    const previous = document.body.style.overflow; document.body.style.overflow = "hidden";
    const escape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", escape);
    return () => { window.clearTimeout(timer); window.removeEventListener("keydown", escape); document.body.style.overflow = previous; openerRef.current?.focus?.(); };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return undefined;
    let cancelled = false; setLoading(true); setError("");
    const timer = window.setTimeout(() => {
      getInventoryWarehouses({ keyword: keyword.trim() || undefined, limit: 50 })
        .then((response) => { if (!cancelled) { setItems(response.items || []); setTotal(response.total || 0); setActiveIndex(-1); } })
        .catch((requestError) => { if (!cancelled) setError(requestError.message || "창고 목록을 불러오지 못했습니다."); })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, 250);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [isOpen, keyword]);

  if (!isOpen) return null;
  const choose = (item) => {
    const next = [item, ...readRecent().filter((row) => row.warehouse_code !== item.warehouse_code)].slice(0, 5);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next)); onSelect(item);
  };
  const handleKeyDown = (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault(); const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => Math.max(0, Math.min(items.length - 1, current + step)));
    } else if (event.key === "Enter" && activeIndex >= 0 && items[activeIndex]) { event.preventDefault(); choose(items[activeIndex]); }
  };
  return createPortal(
    <div className="product-picker-backdrop product-picker-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="product-picker-modal" role="dialog" aria-modal="true" aria-labelledby="warehouse-picker-title">
        <header className="product-picker-heading"><div><h3 id="warehouse-picker-title">창고 및 백화점 선택</h3><p>조회할 창고 또는 백화점을 선택하세요.</p></div><button type="button" onClick={onClose}>닫기</button></header>
        {recent.length ? <div className="product-picker-recent"><strong>최근 조회 장소</strong><div>{recent.map((item) => <button type="button" key={item.warehouse_code} onClick={() => choose(item)}>{item.warehouse_name}</button>)}</div></div> : null}
        <label className="product-picker-search"><span className="sr-only">창고 및 백화점 검색</span><input ref={searchRef} value={keyword} onChange={(event) => setKeyword(event.target.value)} onKeyDown={handleKeyDown} placeholder="창고명, 백화점명, 지점명, 코드 검색" /></label>
        <div className="product-picker-count">검색 결과 {Number(total).toLocaleString("ko-KR")}건</div>
        <div className="product-picker-list" role="listbox" aria-label="창고 및 백화점 목록">
          {items.map((item, index) => <button type="button" role="option" aria-selected={activeIndex === index} className={activeIndex === index ? "active" : ""} key={item.warehouse_code} onClick={() => choose(item)}><strong>{item.warehouse_name}<em>{item.location_type === "department_store" ? "백화점" : "창고"}</em></strong><span>창고코드: {item.warehouse_code}</span></button>)}
          {!loading && !items.length && !error ? <p className="product-picker-empty">검색 조건에 맞는 장소가 없습니다.</p> : null}
          {error ? <p className="product-picker-error">{error}</p> : null}
        </div>
        <footer className="product-picker-footer">{loading ? <p className="product-picker-loading">장소 목록을 불러오는 중입니다.</p> : null}</footer>
      </section>
    </div>, document.body,
  );
}

export default WarehousePickerModal;
