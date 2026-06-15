import React from "react";
import AssetCategoryTabs from "./AssetCategoryTabs.jsx";
import StatusBadge from "./StatusBadge.jsx";

const SORTABLE_COLUMNS = {
  name: "제품명",
  status: "상태",
  serial_number: "시리얼번호",
  department_name: "부서(사용자명)",
};

function AssetList({
  assets,
  isLoading,
  error,
  hasActiveFilters,
  selectedAssetId,
  onSelectAsset,
  sortConfig,
  onSortChange,
  categories,
  activeCategoryId,
  onCategorySelect,
  onOpenCategoryCreate,
}) {
  const safeAssets = Array.isArray(assets) ? assets : [];
  const isSpecificCategorySelected = Boolean(activeCategoryId);

  const renderContent = () => {
    if (isLoading) {
      return <div className="state-panel">자산 목록을 불러오는 중입니다.</div>;
    }

    if (error) {
      return (
        <div className="state-panel state-error">
          <strong>자산 목록을 불러오지 못했습니다.</strong>
          <span>Backend 또는 DB 연결을 확인해주세요.</span>
          <span className="state-detail">{error}</span>
        </div>
      );
    }

    if (safeAssets.length === 0) {
      return (
        <div className="state-panel">
          <strong>
            {isSpecificCategorySelected
              ? "이 분류에 등록된 자산이 없습니다."
              : hasActiveFilters
                ? "현재 조건에 맞는 자산이 없습니다."
                : "등록된 자산이 없습니다."}
          </strong>
          <span>
            {isSpecificCategorySelected
              ? "빠른 등록 또는 상세 등록으로 자산을 추가해보세요."
              : hasActiveFilters
                ? "검색어나 필터 조건을 조정하거나 필터 초기화를 눌러 전체 목록을 확인하세요."
                : "먼저 자산을 등록해주세요. Backend 또는 DB가 준비되지 않은 경우 상태를 확인하세요."}
          </span>
        </div>
      );
    }

    return (
      <>
      <div className="asset-table-wrap">
        <table className="asset-table">
          <thead>
            <tr>
              <SortableHeader column="name" sortConfig={sortConfig} onSortChange={onSortChange}>
                제품명
              </SortableHeader>
              <SortableHeader column="status" sortConfig={sortConfig} onSortChange={onSortChange}>
                상태
              </SortableHeader>
              <SortableHeader
                column="serial_number"
                sortConfig={sortConfig}
                onSortChange={onSortChange}
              >
                시리얼번호
              </SortableHeader>
              <SortableHeader
                column="department_name"
                sortConfig={sortConfig}
                onSortChange={onSortChange}
              >
                부서(사용자명)
              </SortableHeader>
              <th>구매일</th>
            </tr>
          </thead>
          <tbody>
            {safeAssets.map((asset) => (
              <tr
                key={asset.id}
                className={asset.id === selectedAssetId ? "asset-row selected" : "asset-row"}
                onClick={() => onSelectAsset(asset.id)}
                tabIndex="0"
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectAsset(asset.id);
                  }
                }}
              >
                <td>
                  <div className="asset-name">
                    <strong>{asset.name}</strong>
                    <span>ID {asset.id}</span>
                  </div>
                </td>
                <td>
                  <StatusBadge status={asset.status} />
                </td>
                <td>{asset.serial_number || "-"}</td>
                <td>{getDepartmentUserLabel(asset)}</td>
                <td>{asset.purchase_date || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="asset-cards" aria-label="자산 목록">
        {safeAssets.map((asset) => (
          <article
            className={asset.id === selectedAssetId ? "asset-card selected" : "asset-card"}
            key={asset.id}
            onClick={() => onSelectAsset(asset.id)}
            tabIndex="0"
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectAsset(asset.id);
              }
            }}
          >
            <div>
              <strong>{asset.name}</strong>
              <span>
                ID {asset.id}
                {asset.id === selectedAssetId ? " · 선택됨" : ""}
              </span>
            </div>
            <StatusBadge status={asset.status} />
            <dl>
              <dt>시리얼번호</dt>
              <dd>{asset.serial_number || "-"}</dd>
              <dt>부서(사용자명)</dt>
              <dd>{getDepartmentUserLabel(asset)}</dd>
              <dt>구매일</dt>
              <dd>{asset.purchase_date || "-"}</dd>
            </dl>
          </article>
        ))}
      </div>
      </>
    );
  };

  return (
    <div className="asset-list">
      <AssetCategoryTabs
        categories={categories}
        activeCategoryId={activeCategoryId}
        onSelectCategory={onCategorySelect}
        onOpenCreate={onOpenCategoryCreate}
      />
      {renderContent()}
    </div>
  );
}

function getDepartmentUserLabel(asset) {
  return asset?.department_name || asset?.user_name || "-";
}

function SortableHeader({ column, sortConfig, onSortChange, children }) {
  const isActive = sortConfig?.key === column;
  const directionText = sortConfig?.direction === "desc" ? "내림차순" : "오름차순";
  const marker = isActive ? (sortConfig.direction === "desc" ? "↓" : "↑") : "";

  return (
    <th>
      <button
        type="button"
        className={isActive ? "table-sort active" : "table-sort"}
        onClick={() => onSortChange(column)}
        aria-label={`${SORTABLE_COLUMNS[column]} 정렬${isActive ? `, 현재 ${directionText}` : ""}`}
      >
        <span>{children}</span>
        <span aria-hidden="true">{marker}</span>
      </button>
    </th>
  );
}

export default AssetList;
