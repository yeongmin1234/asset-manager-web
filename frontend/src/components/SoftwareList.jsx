import React, { useMemo, useRef, useState } from "react";

const SOFTWARE_COLUMN_WIDTH_STORAGE_KEY = "assetManager.softwareTable.columnWidths";
const SOFTWARE_COLUMNS = [
  { key: "name", label: "소프트웨어명", initialWidth: 220, minWidth: 180 },
  { key: "owner", label: "소유", initialWidth: 140, minWidth: 130 },
  { key: "licenseType", label: "라이선스 구분", initialWidth: 130, minWidth: 110 },
  { key: "quantity", label: "수량", initialWidth: 90, minWidth: 80 },
  { key: "price", label: "가격", initialWidth: 120, minWidth: 110 },
  { key: "expireDate", label: "만료일", initialWidth: 140, minWidth: 100 },
  { key: "licenseKey", label: "라이선스키/CDKEY", initialWidth: 150, minWidth: 130 },
  { key: "actions", label: "관리", initialWidth: 120, minWidth: 100 },
];

function SoftwareList({
  items,
  isLoading,
  error,
  filters,
  activeTab,
  editingItemId,
  onDelete,
  onEdit,
  onFilterChange,
  onTabChange,
  tabs,
}) {
  const [expandedLicenseId, setExpandedLicenseId] = useState(null);
  const [copiedLicenseId, setCopiedLicenseId] = useState(null);
  const [columnWidths, setColumnWidths] = useState(() =>
    getInitialColumnWidths(SOFTWARE_COLUMNS, SOFTWARE_COLUMN_WIDTH_STORAGE_KEY),
  );
  const resizeStateRef = useRef(null);
  const copyResetTimerRef = useRef(null);
  const safeItems = Array.isArray(items) ? items : [];
  const safeTabs = Array.isArray(tabs) ? tabs : [];
  const hasActiveFilters = Boolean(activeTab || filters.expiration_status);

  const tableWidth = useMemo(
    () => SOFTWARE_COLUMNS.reduce((total, column) => total + columnWidths[column.key], 0),
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
    document.body.classList.add("software-column-resizing");

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
        saveColumnWidths(SOFTWARE_COLUMN_WIDTH_STORAGE_KEY, nextWidths);
        return nextWidths;
      });
    };

    const handleMouseUp = () => {
      resizeStateRef.current = null;
      document.body.classList.remove("software-column-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  const toggleLicense = (itemId) => {
    setExpandedLicenseId((currentId) => (currentId === itemId ? null : itemId));
    setCopiedLicenseId(null);
  };

  const handleCopyLicense = async (item) => {
    const licenseKey = item?.license_key || "";
    if (!licenseKey) {
      return;
    }

    try {
      await navigator.clipboard.writeText(licenseKey);
      setCopiedLicenseId(item.id);
      window.clearTimeout(copyResetTimerRef.current);
      copyResetTimerRef.current = window.setTimeout(() => {
        setCopiedLicenseId(null);
      }, 1400);
    } catch {
      setCopiedLicenseId(null);
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return <div className="state-panel">SW 목록을 불러오는 중입니다.</div>;
    }
    if (error) {
      return (
        <div className="state-panel state-error">
          <strong>SW 목록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      );
    }
    return (
      <div className="asset-table-wrap">
        <table className="asset-table software-table software-resizable-table" style={{ minWidth: `${tableWidth}px` }}>
          <colgroup>
            {SOFTWARE_COLUMNS.map((column) => (
              <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {SOFTWARE_COLUMNS.map((column) => (
                <th key={column.key}>
                  <span className="resizable-table-heading">{column.label}</span>
                  <span
                    aria-hidden="true"
                    className="table-column-resize-handle"
                    onMouseDown={(event) => handleColumnResizeStart(event, column)}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {safeItems.length === 0 ? (
              <tr>
                <td colSpan={SOFTWARE_COLUMNS.length}>
                  <div className="state-panel asset-table-empty-state">
                    <strong>{hasActiveFilters ? "현재 조건에 맞는 SW가 없습니다." : "등록된 SW가 없습니다."}</strong>
                    <span>빠른 등록 폼으로 소프트웨어를 추가해주세요.</span>
                  </div>
                </td>
              </tr>
            ) : safeItems.map((item) => (
              <tr
                key={item.id}
                className={editingItemId === item.id ? "software-row editing" : "software-row"}
              >
                <td>
                  <div className="asset-name">
                    <strong>{item.name}</strong>
                    <span>ID {item.id}</span>
                  </div>
                </td>
                <td>{item.owner_name || "-"}</td>
                <td>
                  <span className={`software-license-badge ${getLicenseTypeClass(item.license_type)}`}>
                    {item.license_type}
                  </span>
                </td>
                <td>{Number(item.quantity || 0).toLocaleString("ko-KR")}</td>
                <td className="software-price-cell">{formatPrice(item.price_amount)}</td>
                <td>
                  <div className="software-expire-cell">
                    <span className="software-expiry-date">{formatCompactDate(item.expire_date)}</span>
                    <ExpirationBadge expireDate={item.expire_date} />
                  </div>
                </td>
                <td className="software-license-key-cell">
                  {item.license_key ? (
                    expandedLicenseId === item.id ? (
                      <div className="software-license-inline">
                        <span className="software-license-key-text" title={item.license_key}>
                          {item.license_key}
                        </span>
                        <button
                          type="button"
                          className="secondary-button software-license-copy-button"
                          onClick={() => handleCopyLicense(item)}
                        >
                          {copiedLicenseId === item.id ? "복사됨" : "복사"}
                        </button>
                        <button
                          type="button"
                          className="secondary-button software-license-view-button"
                          onClick={() => toggleLicense(item.id)}
                        >
                          숨기기
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="secondary-button software-license-view-button"
                        onClick={() => toggleLicense(item.id)}
                      >
                        라이선스 보기
                      </button>
                    )
                  ) : (
                    "-"
                  )}
                </td>
                <td>
                  <div className="software-row-actions">
                    <button
                      type="button"
                      className="secondary-button software-action-button"
                      onClick={() => onEdit(item)}
                    >
                      수정
                    </button>
                    <button
                      type="button"
                      className="danger-button software-action-button"
                      onClick={() => onDelete(item)}
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <section className="content-panel software-list-panel">
      <div className="section-heading">
        <div>
          <h2>SW 목록</h2>
          <p>탭과 만료 상태를 기준으로 최신 등록순으로 표시됩니다.</p>
        </div>
      </div>

      <div className="software-list-controls">
        <div className="software-tabs" aria-label="SW 구분 탭">
          {safeTabs.map((tab) => (
            <button
              type="button"
              key={tab.label}
              className={
                activeTab === tab.value
                  ? `software-tab ${getSoftwareTabClass(tab.value)} active`
                  : `software-tab ${getSoftwareTabClass(tab.value)}`
              }
              onClick={() => onTabChange(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="software-filter-grid">
          <label className="field">
            <span>만료 상태</span>
            <select
              value={filters.expiration_status}
              onChange={(event) =>
                onFilterChange({ ...filters, expiration_status: event.target.value })
              }
            >
              <option value="">전체</option>
              <option value="within_30">만료 예정 30일 이내</option>
              <option value="within_60">만료 예정 60일 이내</option>
              <option value="within_90">만료 예정 90일 이내</option>
              <option value="expired">만료됨</option>
              <option value="no_date">만료일 없음</option>
            </select>
          </label>
        </div>
      </div>

      {renderContent()}
    </section>
  );
}

function ExpirationBadge({ expireDate }) {
  const status = getExpirationStatus(expireDate);
  return (
    <span className={`software-expiration-badge software-expiry-status software-expiration-${status.tone}`}>
      {status.label}
    </span>
  );
}

function getLicenseTypeClass(licenseType) {
  if (licenseType === "영구") {
    return "permanent";
  }
  if (licenseType === "구독") {
    return "subscription";
  }
  if (licenseType === "사용중지") {
    return "inactive";
  }
  return "unknown";
}

function getSoftwareTabClass(value) {
  if (value === "영구") {
    return "software-tab-permanent";
  }
  if (value === "구독") {
    return "software-tab-subscription";
  }
  if (value === "사용중지") {
    return "software-tab-inactive";
  }
  return "software-tab-all";
}

function formatCompactDate(value) {
  if (!value) {
    return "-";
  }
  const text = String(value);
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return text;
  }
  return `${match[1].slice(2)}-${match[2]}-${match[3]}`;
}

function getExpirationStatus(expireDate) {
  const daysLeft = getDaysUntilExpire(expireDate);
  if (daysLeft === null) {
    return { label: "만료일 없음", tone: "muted" };
  }
  if (daysLeft < 0) {
    return { label: "만료됨", tone: "expired" };
  }
  if (daysLeft <= 30) {
    return { label: "30일 이내", tone: "danger" };
  }
  if (daysLeft <= 60) {
    return { label: "60일 이내", tone: "warning" };
  }
  if (daysLeft <= 90) {
    return { label: "90일 이내", tone: "notice" };
  }
  return { label: "정상", tone: "normal" };
}

function getDaysUntilExpire(expireDate) {
  if (!expireDate) {
    return null;
  }

  const [year, month, day] = String(expireDate).split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const expireStart = new Date(year, month - 1, day);
  return Math.ceil((expireStart.getTime() - todayStart.getTime()) / 86400000);
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }
  return `₩${numericValue.toLocaleString("ko-KR")}`;
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

export default SoftwareList;
