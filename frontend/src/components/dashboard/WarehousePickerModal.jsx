import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getInventoryWarehouses } from "../../api/client.js";

const PAGE_SIZE = 50;

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
  const requestIdRef = useRef(0);

  const load = async ({ search, offset = 0, append = false }) => {
    const requestId = ++requestIdRef.current;
    setLoading(true); setError("");
    try {
      const response = await getInventoryWarehouses({ keyword: search.trim() || undefined, offset, limit: PAGE_SIZE });
      if (requestId !== requestIdRef.current) return;
      const incoming = Array.isArray(response.items) ? response.items : [];
      setItems((current) => {
        const merged = append ? [...current, ...incoming] : incoming;
        return [...new Map(merged.map((item) => [item.warehouse_code, item])).values()];
      });
      setTotal(Number(response.total) || 0); setActiveIndex(-1);
    } catch (requestError) {
      if (requestId === requestIdRef.current) {
        setItems([]); setTotal(0); setError(requestError.message || "창고 목록을 불러오지 못했습니다.");
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return undefined;
    openerRef.current = document.activeElement;
    setKeyword(""); setItems([]); setTotal(0); setActiveIndex(-1); setError("");
    load({ search: "" });
    const timer = window.setTimeout(() => searchRef.current?.focus(), 0);
    const previous = document.body.style.overflow; document.body.style.overflow = "hidden";
    const escape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", escape);
    return () => {
      requestIdRef.current += 1; window.clearTimeout(timer); window.removeEventListener("keydown", escape);
      document.body.style.overflow = previous; openerRef.current?.focus?.();
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || keyword === "") return undefined;
    const timer = window.setTimeout(() => load({ search: keyword }), 300);
    return () => window.clearTimeout(timer);
  }, [isOpen, keyword]);

  const groups = useMemo(() => [
    ["파주 창고", items.filter((item) => (item.display_name || item.warehouse_name || "").includes("파주"))],
    ["백화점", items.filter((item) => item.location_type === "department_store" && !(item.display_name || item.warehouse_name || "").includes("파주"))],
    ["기타 창고", items.filter((item) => item.location_type !== "department_store" && !(item.display_name || item.warehouse_name || "").includes("파주"))],
  ].filter(([, rows]) => rows.length), [items]);

  if (!isOpen) return null;
  const choose = (item) => {
    setRecent((current) => [
      { warehouse_code: item.warehouse_code, display_name: item.display_name || item.warehouse_name, warehouse_name: item.warehouse_name, location_type: item.location_type },
      ...current.filter((row) => row.warehouse_code !== item.warehouse_code),
    ].slice(0, 5));
    onSelect(item);
  };
  const handleKeywordChange = (event) => {
    const value = event.target.value; setKeyword(value);
    if (!value) load({ search: "" });
  };
  const handleKeyDown = (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault(); const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => Math.max(0, Math.min(items.length - 1, current + step)));
    } else if (event.key === "Enter" && activeIndex >= 0 && items[activeIndex]) { event.preventDefault(); choose(items[activeIndex]); }
  };
  const renderItem = (item) => {
    const index = items.findIndex((row) => row.warehouse_code === item.warehouse_code);
    const departmentStore = item.location_type === "department_store";
    return <button type="button" role="option" aria-selected={activeIndex === index} className={activeIndex === index ? "active" : ""} key={item.warehouse_code} onClick={() => choose(item)}><strong>{item.display_name || item.warehouse_name}<em>{departmentStore ? "백화점" : item.location_type === "warehouse" ? "창고" : "기타"}</em></strong><span>{departmentStore ? "장소코드" : "창고코드"}: {item.warehouse_code}</span></button>;
  };
  return createPortal(
    <div className="product-picker-backdrop product-picker-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="product-picker-modal" role="dialog" aria-modal="true" aria-labelledby="warehouse-picker-title">
        <header className="product-picker-heading"><div><h3 id="warehouse-picker-title">창고 및 백화점 선택</h3><p>조회할 창고 또는 백화점을 선택하세요.</p></div><button type="button" onClick={onClose}>닫기</button></header>
        {recent.length ? <div className="product-picker-recent"><strong>최근 조회 장소</strong><div>{recent.map((item) => <button type="button" key={item.warehouse_code} onClick={() => choose(item)}>{item.display_name}</button>)}</div></div> : null}
        <label className="product-picker-search"><span className="sr-only">창고 및 백화점 검색</span><input ref={searchRef} value={keyword} onChange={handleKeywordChange} onKeyDown={handleKeyDown} placeholder="창고명, 백화점명, 지점명, 코드 검색" /></label>
        <div className="product-picker-count">검색 결과 {Number(total).toLocaleString("ko-KR")}건</div>
        <div className="product-picker-list warehouse-picker-list" role="listbox" aria-label="창고 및 백화점 목록">
          {groups.map(([label, rows]) => <section className="warehouse-picker-group" key={label}><h4>{label}</h4>{rows.map(renderItem)}</section>)}
          {!loading && !items.length && !error ? <p className="product-picker-empty">검색 조건에 맞는 장소가 없습니다.</p> : null}
          {error ? <p className="product-picker-error">창고 목록을 불러오지 못했습니다.</p> : null}
        </div>
        <footer className="product-picker-footer">
          {loading ? <p className="product-picker-loading">장소 목록을 불러오는 중입니다.</p> : null}
          {!loading && !error && items.length < total ? <button type="button" onClick={() => load({ search: keyword, offset: items.length, append: true })}>더 보기</button> : null}
        </footer>
      </section>
    </div>, document.body,
  );
}

export default WarehousePickerModal;
