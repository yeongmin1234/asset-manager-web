import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getInventoryProducts } from "../../api/client.js";

const RECENT_PRODUCTS_KEY = "assetManager.recentInventoryProducts";
const PAGE_SIZE = 50;

export function readRecentInventoryProducts() {
  try {
    const items = JSON.parse(window.localStorage.getItem(RECENT_PRODUCTS_KEY) || "[]");
    return Array.isArray(items) ? items.slice(0, 5) : [];
  } catch {
    return [];
  }
}

export function rememberRecentInventoryProduct(item) {
  const recent = readRecentInventoryProducts().filter((entry) => entry.item_code !== item.item_code);
  window.localStorage.setItem(RECENT_PRODUCTS_KEY, JSON.stringify([item, ...recent].slice(0, 5)));
}

function ProductPickerModal({ isOpen, onClose, onSelect }) {
  const [keyword, setKeyword] = useState("");
  const [debouncedKeyword, setDebouncedKeyword] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recent, setRecent] = useState([]);
  const searchRef = useRef(null);
  const optionRefs = useRef([]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedKeyword(keyword.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [keyword]);

  useEffect(() => {
    if (!isOpen) return;
    setKeyword("");
    setDebouncedKeyword("");
    setItems([]);
    setPage(1);
    setActiveIndex(-1);
    setRecent(readRecentInventoryProducts());
    const focusTimer = window.setTimeout(() => searchRef.current?.focus(), 0);
    return () => window.clearTimeout(focusTimer);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    let cancelled = false;
    setIsLoading(true);
    setError("");
    getInventoryProducts({ keyword: debouncedKeyword || undefined, page: 1, pageSize: PAGE_SIZE })
      .then((response) => {
        if (cancelled) return;
        setItems(Array.isArray(response.items) ? response.items : []);
        setTotal(Number(response.total || 0));
        setPage(1);
        setActiveIndex(-1);
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message || "품목 목록을 불러오지 못했습니다.");
      })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [debouncedKeyword, isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleEscape = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (activeIndex < 0) return;
    optionRefs.current[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  if (!isOpen) return null;

  const choose = (item) => {
    rememberRecentInventoryProduct(item);
    onSelect(item);
  };

  const handleSearchKeyDown = (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!items.length) return;
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) => Math.max(0, Math.min(items.length - 1, current + step)));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0 && items[activeIndex]) choose(items[activeIndex]);
      else if (items.length === 1 && total === 1) choose(items[0]);
    }
  };

  const loadMore = async () => {
    if (isLoading || items.length >= total) return;
    const nextPage = page + 1;
    setIsLoading(true);
    try {
      const response = await getInventoryProducts({
        keyword: debouncedKeyword || undefined, page: nextPage, pageSize: PAGE_SIZE,
      });
      setItems((current) => [...current, ...(Array.isArray(response.items) ? response.items : [])]);
      setPage(nextPage);
    } catch (requestError) {
      setError(requestError.message || "품목 목록을 더 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const modal = (
    <div
      className="product-picker-backdrop product-picker-overlay"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="product-picker-modal" role="dialog" aria-modal="true" aria-labelledby="product-picker-title">
        <header className="product-picker-heading">
          <div><h3 id="product-picker-title">품목 선택</h3><p>조회할 품목을 검색하거나 목록에서 선택하세요.</p></div>
          <button type="button" onClick={onClose} aria-label="품목 선택 닫기">닫기</button>
        </header>
        {recent.length ? (
          <div className="product-picker-recent"><strong>최근 조회 품목</strong><div>{recent.map((item) => <button type="button" key={item.item_code} onClick={() => choose(item)}>{item.item_name || item.item_code}</button>)}</div></div>
        ) : null}
        <label className="product-picker-search">
          <span className="sr-only">품목 검색</span>
          <input ref={searchRef} value={keyword} onChange={(event) => setKeyword(event.target.value)} onKeyDown={handleSearchKeyDown} placeholder="품목명, 코드, 규격, 바코드로 검색" autoComplete="off" />
        </label>
        <div className="product-picker-count">검색 결과 {total.toLocaleString("ko-KR")}건</div>
        <div className="product-picker-list" role="listbox" aria-label="전체 품목 목록">
          {items.map((item, index) => (
            <button ref={(element) => { optionRefs.current[index] = element; }} type="button" role="option" aria-selected={activeIndex === index} className={activeIndex === index ? "active" : ""} key={item.item_code} onClick={() => choose(item)}>
              <strong>{item.item_name || "품목명 없음"}</strong>
              <span>{[item.item_code, item.size, item.unit].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
          {!isLoading && !items.length && !error ? <p className="product-picker-empty">검색 조건에 맞는 품목이 없습니다.</p> : null}
          {error && !items.length ? <p className="product-picker-error">{error}</p> : null}
        </div>
        <footer className="product-picker-footer">
          {error && items.length ? <p className="product-picker-error">{error}</p> : null}
          {isLoading ? <p className="product-picker-loading">품목을 불러오는 중입니다.</p> : null}
          {!isLoading && items.length < total ? <button type="button" className="product-picker-more" onClick={loadMore}>더 보기</button> : null}
        </footer>
      </section>
    </div>
  );

  return createPortal(modal, document.body);
}

export default ProductPickerModal;
