import React from "react";
import { RECALL_STATUS_OPTIONS } from "./onlineDisplayUtils.js";

function RecallFilters({ values, onChange, onSearch, onReset, isLoading }) {
  const update = (key, value) => onChange({ ...values, [key]: value });
  return (
    <form className="online-recall-filters" aria-label="리콜 검색 및 필터" onSubmit={(event) => { event.preventDefault(); onSearch(); }}>
      <input
        type="search"
        value={values.keyword}
        onChange={(event) => update("keyword", event.target.value)}
        placeholder="고객명, 연락처, 시리얼번호 검색"
        aria-label="리콜 검색"
      />
      <select value={values.status} onChange={(event) => update("status", event.target.value)} aria-label="상태 필터">
        <option value="">전체 상태</option>
        {RECALL_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <select value="" aria-label="채널 필터" disabled title="판매 채널 데이터 형식 확정 후 지원 예정">
        <option value="">전체 채널</option>
      </select>
      <button type="submit" className="primary-action" disabled={isLoading}>조회</button>
      <button type="button" className="secondary-button" onClick={onReset} disabled={isLoading}>초기화</button>
    </form>
  );
}

export default RecallFilters;
