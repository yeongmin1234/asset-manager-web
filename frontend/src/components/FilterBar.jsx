import React from "react";

const STATUS_OPTIONS = [
  { label: "전체", value: "" },
  { label: "사용중", value: "사용중" },
  { label: "미사용", value: "미사용" },
  { label: "폐기", value: "폐기" },
];

const LOCATION_OPTIONS = [
  { label: "전체", value: "" },
  { label: "본사", value: "본사" },
  { label: "백화점", value: "백화점" },
  { label: "파주창고", value: "파주창고" },
  { label: "기타", value: "기타" },
];

function FilterBar({
  filters,
  categories,
  departments,
  isLookupDisabled,
  onFilterChange,
  onRefresh,
  onReset,
  onOpenCreate,
  onExportExcel,
  isLoading,
  isExporting,
  hasActiveFilters,
  sortControl,
  canManage = true,
}) {
  const handleChange = (event) => {
    onFilterChange({
      ...filters,
      [event.target.name]: event.target.value,
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onRefresh();
  };

  return (
    <form className="toolbar" aria-label="자산 목록 필터" onSubmit={handleSubmit}>
      <div className="filter-grid">
        <label className="field">
          <span>검색어</span>
          <input
            name="keyword"
            value={filters.keyword}
            onChange={handleChange}
            placeholder="제품명, 모델명, 시리얼번호, 부서/사용자 검색"
          />
        </label>

        <label className="field">
          <span>상태</span>
          <select name="status" value={filters.status} onChange={handleChange}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>분류</span>
          <select
            name="category_id"
            value={filters.category_id}
            onChange={handleChange}
            disabled={isLookupDisabled}
          >
            <option value="">전체</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>위치</span>
          <select name="location_group" value={filters.location_group} onChange={handleChange}>
            {LOCATION_OPTIONS.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>부서(사용자명)</span>
          <select
            name="department_id"
            value={filters.department_id}
            onChange={handleChange}
            disabled={isLookupDisabled}
          >
            <option value="">전체</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="toolbar-actions">
        {sortControl}
        <button
          type="button"
          className="secondary-button"
          onClick={onReset}
          disabled={isLoading || !hasActiveFilters}
        >
          필터 초기화
        </button>
        <button type="submit" className="secondary-button" disabled={isLoading}>
          {isLoading ? "새로고침 중..." : "목록 새로고침"}
        </button>
        <button
          type="button"
          className="secondary-button export-button"
          onClick={onExportExcel}
          disabled={isExporting}
        >
          {isExporting ? "다운로드 중..." : "엑셀 내보내기"}
        </button>
        {canManage ? (
          <button type="button" className="primary-action" onClick={onOpenCreate}>
            상세 등록
          </button>
        ) : null}
      </div>
    </form>
  );
}

export default FilterBar;
