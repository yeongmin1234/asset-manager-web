import React from "react";

export const RECALL_PAGE_SIZES = [10, 20, 50, 100];
const STORAGE_KEY = "onlineRecall.pageSize";

export function readRecallPageSize() {
  try {
    const value = Number(window.localStorage.getItem(STORAGE_KEY));
    return RECALL_PAGE_SIZES.includes(value) ? value : 20;
  } catch {
    return 20;
  }
}

export function saveRecallPageSize(value) {
  if (!RECALL_PAGE_SIZES.includes(value)) return;
  try { window.localStorage.setItem(STORAGE_KEY, String(value)); }
  catch { /* The selection still works when browser storage is unavailable. */ }
}

export default function RecallPageSizeSelect({ value, onChange, disabled = false }) {
  return <label className="online-recall-page-size">페이지당 표시
    <select aria-label="페이지당 표시 건수" value={value} onChange={(event) => {
      const nextSize = Number(event.target.value);
      if (RECALL_PAGE_SIZES.includes(nextSize)) onChange(nextSize);
    }} disabled={disabled}>
      {RECALL_PAGE_SIZES.map((size) => <option key={size} value={size}>{size}건</option>)}
    </select>
  </label>;
}
