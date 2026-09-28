import React from "react";

function RecallFilters() {
  return (
    <div className="online-recall-filters" role="group" aria-label="리콜 검색 및 필터">
      <input type="search" placeholder="주문번호, 고객명, 시리얼번호 검색" aria-label="리콜 검색" />
      <select defaultValue="" aria-label="상태 필터">
        <option value="">전체 상태</option>
      </select>
      <select defaultValue="" aria-label="채널 필터">
        <option value="">전체 채널</option>
      </select>
    </div>
  );
}

export default RecallFilters;
