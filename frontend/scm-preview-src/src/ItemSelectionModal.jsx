import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { searchECountItems } from "./services/homeAssistantService";
import SkoomiMascot from "./components/common/SkoomiMascot";
export default function ItemSelectionModal({ candidates = [], recent = [], onSelect, onClose, returnFocusRef }) {
  const [query, setQuery] = useState(""), [items, setItems] = useState(candidates), [loading, setLoading] = useState(false), [active, setActive] = useState(0);
  const listRef = useRef(null);
  useEffect(() => { const timer = window.setTimeout(() => { setLoading(true); searchECountItems(query).then((data) => { setItems(data.items || []); setActive(0); }).catch(() => setItems([])).finally(() => setLoading(false)); }, 300); return () => window.clearTimeout(timer); }, [query]);
  useEffect(() => () => returnFocusRef?.current?.focus(), [returnFocusRef]);
  useEffect(() => { listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" }); }, [active]);
  const mascotState = loading ? "searching" : items.length ? "guide" : "empty";
  const mascotMessage = loading ? "품목을 찾고 있어요." : items.length ? "조회할 품목을 선택해주세요." : "일치하는 품목이 없어요.";
  const keys = (e) => { if (e.key === "Escape") onClose(); if (e.key === "ArrowDown") { e.preventDefault(); setActive((v) => Math.min(v + 1, items.length - 1)); } if (e.key === "ArrowUp") { e.preventDefault(); setActive((v) => Math.max(v - 1, 0)); } if (e.key === "Enter" && items[active]) { e.preventDefault(); onSelect(items[active]); } };
  return createPortal(<div className="ai-modal-layer"><section className="ai-modal ai-item-modal" onKeyDown={keys}><header><div><h2>이카운트 품목 선택</h2><p>품목을 선택하기 전에는 재고 API를 호출하지 않습니다.</p></div><button type="button" onClick={onClose}>닫기</button></header>
    <input autoFocus className="ai-item-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="품목명 또는 품목코드 검색" />
    {!query && recent.length > 0 && <div className="ai-recent-items"><b>최근 조회</b>{recent.slice(0, 5).map((item) => <button type="button" key={item.item_code} onClick={() => onSelect(item)}>{item.item_name}</button>)}</div>}
    <div className="ai-item-mascot"><SkoomiMascot state={mascotState} size="small" message={mascotMessage}/></div>
    <p className="ai-item-count" aria-live="polite">{loading ? "검색 중..." : `검색 결과 ${items.length}건`}</p>
    <div className="ai-modal-list" ref={listRef}>{items.map((item, index) => <button type="button" data-index={index} className={active === index ? "active" : ""} key={item.item_code} onMouseEnter={() => setActive(index)} onClick={() => onSelect(item)}><strong>{item.item_name}</strong><span>{item.item_code} · {item.specification || "규격 없음"}</span></button>)}</div>
  </section></div>, document.body);
}
