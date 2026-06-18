import React, { useMemo, useRef, useState } from "react";
import AssetCategoryTabs from "./AssetCategoryTabs.jsx";
import StatusBadge from "./StatusBadge.jsx";

const SORTABLE_COLUMNS = {
  name: "제품명",
  status: "상태",
  serial_number: "시리얼번호",
  department_name: "부서(사용자명)",
};

const LOCATION_TABS = ["", "본사", "백화점", "파주창고", "기타"];
const ASSET_COLUMN_WIDTH_STORAGE_KEY = "assetManager.assetTable.columnWidths";
const ASSET_COLUMNS = [
  { key: "name", label: "제품명", initialWidth: 220, minWidth: 160, sortable: true },
  { key: "status", label: "상태", initialWidth: 100, minWidth: 90, sortable: true },
  { key: "serial", label: "시리얼번호", initialWidth: 150, minWidth: 140, sortable: true, sortKey: "serial_number" },
  { key: "department", label: "부서(사용자명)", initialWidth: 170, minWidth: 150, sortable: true, sortKey: "department_name" },
  { key: "location", label: "위치", initialWidth: 160, minWidth: 90 },
  { key: "purchaseDate", label: "구매일", initialWidth: 120, minWidth: 100 },
];

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
  activeLocationGroup,
  onLocationSelect,
  onOpenCategoryCreate,
}) {
  const safeAssets = Array.isArray(assets) ? assets : [];
  const isSpecificCategorySelected = Boolean(activeCategoryId);
  const [columnWidths, setColumnWidths] = useState(() =>
    getInitialColumnWidths(ASSET_COLUMNS, ASSET_COLUMN_WIDTH_STORAGE_KEY),
  );
  const resizeStateRef = useRef(null);

  const tableWidth = useMemo(
    () => ASSET_COLUMNS.reduce((total, column) => total + columnWidths[column.key], 0),
    [columnWidths],
  );

  const handleColumnResizeStart = (event, column) => {
    event.preventDefault();
    event.stopPropagation();
    resizeStateRef.current = {
      key: column.key,
      minWidth: column.minWidth,
      startX: event.clientX,
      startWidth: columnWidths[column.key],
    };
    document.body.classList.add("asset-column-resizing");

    const handleMouseMove = (moveEvent) => {
      const resizeState = resizeStateRef.current;
      if (!resizeState) {
        return;
      }
      const nextWidth = Math.max(
        resizeState.minWidth,
        resizeState.startWidth + moveEvent.clientX - resizeState.startX,
      );
      setColumnWidths((currentWidths) => {
        const nextWidths = { ...currentWidths, [resizeState.key]: nextWidth };
        saveColumnWidths(ASSET_COLUMN_WIDTH_STORAGE_KEY, nextWidths);
        return nextWidths;
      });
    };

    const handleMouseUp = () => {
      resizeStateRef.current = null;
      document.body.classList.remove("asset-column-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

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

    return (
      <>
      <div className="asset-table-wrap">
        <table className="asset-table asset-resizable-table" style={{ minWidth: `${tableWidth}px` }}>
          <colgroup>
            {ASSET_COLUMNS.map((column) => (
              <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {ASSET_COLUMNS.map((column) => (
                <ResizableHeader
                  key={column.key}
                  column={column}
                  sortConfig={sortConfig}
                  onSortChange={onSortChange}
                  onResizeStart={handleColumnResizeStart}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {safeAssets.length === 0 ? (
              <tr>
                <td colSpan={ASSET_COLUMNS.length}>
                  <div className="state-panel asset-table-empty-state">
                    <strong>
                      {isSpecificCategorySelected
                        ? "이 분류에 등록된 자산이 없습니다."
                        : hasActiveFilters
                          ? "현재 조건에 맞는 자산이 없습니다."
                          : "등록된 자산이 없습니다."}
                    </strong>
                    <span>
                      {hasActiveFilters
                        ? "검색어나 필터 조건을 조정하거나 필터 초기화를 눌러 전체 목록을 확인하세요."
                        : "빠른 등록 또는 상세 등록으로 자산을 추가해보세요."}
                    </span>
                  </div>
                </td>
              </tr>
            ) : safeAssets.map((asset) => (
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
                  </div>
                </td>
                <td>
                  <StatusBadge status={asset.status} />
                </td>
                <td>{asset.serial_number || "-"}</td>
                <td>{getDepartmentUserLabel(asset)}</td>
                <td>{getLocationLabel(asset)}</td>
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
              {asset.id === selectedAssetId && <span>선택됨</span>}
            </div>
            <StatusBadge status={asset.status} />
            <dl>
              <dt>시리얼번호</dt>
              <dd>{asset.serial_number || "-"}</dd>
              <dt>부서(사용자명)</dt>
              <dd>{getDepartmentUserLabel(asset)}</dd>
              <dt>위치</dt>
              <dd>{getLocationLabel(asset)}</dd>
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
      <div className="asset-location-tabs" aria-label="위치별 보기">
        <span>위치별 보기</span>
        {LOCATION_TABS.map((location) => (
          <button
            type="button"
            key={location || "all"}
            className={activeLocationGroup === location ? "asset-location-tab active" : "asset-location-tab"}
            onClick={() => onLocationSelect?.(location)}
          >
            {location || "전체"}
          </button>
        ))}
      </div>
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

function getLocationLabel(asset) {
  const group = asset?.location_group || "";
  const detail = asset?.location_detail || "";
  if (group && detail) {
    return `${group} / ${detail}`;
  }
  return group || detail || "-";
}

function ResizableHeader({ column, sortConfig, onSortChange, onResizeStart }) {
  const sortKey = column.sortKey || column.key;
  const isActive = sortConfig?.key === sortKey;
  const directionText = sortConfig?.direction === "desc" ? "내림차순" : "오름차순";
  const marker = isActive ? (sortConfig.direction === "desc" ? "↓" : "↑") : "";

  return (
    <th>
      {column.sortable ? (
        <button
          type="button"
          className={isActive ? "table-sort active" : "table-sort"}
          onClick={() => onSortChange(sortKey)}
          aria-label={`${SORTABLE_COLUMNS[sortKey]} 정렬${isActive ? `, 현재 ${directionText}` : ""}`}
        >
          <span>{column.label}</span>
          <span aria-hidden="true">{marker}</span>
        </button>
      ) : (
        <span className="resizable-table-heading">{column.label}</span>
      )}
      <span
        aria-hidden="true"
        className="table-column-resize-handle"
        onMouseDown={(event) => onResizeStart(event, column)}
      />
    </th>
  );
}

function getInitialColumnWidths(columns, storageKey) {
  const defaultWidths = columns.reduce(
    (widths, column) => ({ ...widths, [column.key]: column.initialWidth }),
    {},
  );

  if (typeof window === "undefined") {
    return defaultWidths;
  }

  try {
    const savedWidths = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
    return columns.reduce((widths, column) => {
      const savedWidth = Number(savedWidths[column.key]);
      return {
        ...widths,
        [column.key]: Number.isFinite(savedWidth)
          ? Math.max(column.minWidth, savedWidth)
          : column.initialWidth,
      };
    }, {});
  } catch {
    return defaultWidths;
  }
}

function saveColumnWidths(storageKey, widths) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(storageKey, JSON.stringify(widths));
  } catch {
    // Ignore storage failures; resizing still works for the current page state.
  }
}

export default AssetList;
