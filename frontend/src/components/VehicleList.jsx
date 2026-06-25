import React, { Fragment, useMemo, useRef, useState } from "react";

const COLUMN_WIDTH_STORAGE_KEY = "assetManager.vehicleTable.columnWidths";
const VEHICLE_COLUMNS = [
  { key: "company", label: "사업자", initialWidth: 110, minWidth: 80 },
  { key: "vehicleNumber", label: "차량번호", initialWidth: 120, minWidth: 90 },
  { key: "vehicleName", label: "차명", initialWidth: 280, minWidth: 160 },
  { key: "driver", label: "사용자", initialWidth: 100, minWidth: 80 },
  { key: "ownership", label: "소유권", initialWidth: 80, minWidth: 70 },
  { key: "insuranceCompany", label: "보험사", initialWidth: 110, minWidth: 90 },
  { key: "insuranceType", label: "자동차보험 유형", initialWidth: 120, minWidth: 90 },
  { key: "insuranceStart", label: "보험 시작일", initialWidth: 120, minWidth: 100 },
  { key: "insuranceEnd", label: "보험 종료일", initialWidth: 120, minWidth: 100 },
  { key: "insuranceDDay", label: "보험 D-Day", initialWidth: 90, minWidth: 80 },
  { key: "leaseDetail", label: "리스 상세", initialWidth: 100, minWidth: 90 },
  { key: "actions", label: "관리", initialWidth: 120, minWidth: 100 },
];

function VehicleList({
  items,
  isLoading,
  error,
  activeTab,
  activeCompanyTab,
  companyTabs,
  editingItemId,
  onDelete,
  onEdit,
  onCompanyTabChange,
  onTabChange,
  tabs,
}) {
  const safeItems = Array.isArray(items) ? items : [];
  const safeTabs = Array.isArray(tabs) ? tabs : [];
  const safeCompanyTabs = Array.isArray(companyTabs) ? companyTabs : [];
  const [expandedItemId, setExpandedItemId] = useState(null);
  const [columnWidths, setColumnWidths] = useState(getInitialColumnWidths);
  const resizeStateRef = useRef(null);

  const tableWidth = useMemo(
    () => VEHICLE_COLUMNS.reduce((total, column) => total + columnWidths[column.key], 0),
    [columnWidths],
  );

  const handleColumnResizeStart = (event, column) => {
    event.preventDefault();
    resizeStateRef.current = {
      key: column.key,
      minWidth: column.minWidth,
      startX: event.clientX,
      startWidth: columnWidths[column.key],
    };
    document.body.classList.add("vehicle-column-resizing");

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
        saveColumnWidths(nextWidths);
        return nextWidths;
      });
    };

    const handleMouseUp = () => {
      resizeStateRef.current = null;
      document.body.classList.remove("vehicle-column-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  const renderContent = () => {
    if (isLoading) {
      return <div className="state-panel">차량 목록을 불러오는 중입니다.</div>;
    }
    if (error) {
      return (
        <div className="state-panel state-error">
          <strong>차량 목록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      );
    }
    if (safeItems.length === 0) {
      return (
        <div className="state-panel">
          <strong>{activeTab ? "현재 조건에 맞는 차량이 없습니다." : "등록된 차량이 없습니다."}</strong>
          <span>빠른 등록 폼으로 차량을 추가해주세요.</span>
        </div>
      );
    }

    return (
      <div className="asset-table-wrap vehicle-table-wrap">
        <table className="asset-table vehicle-table" style={{ minWidth: `${tableWidth}px` }}>
          <colgroup>
            {VEHICLE_COLUMNS.map((column) => (
              <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {VEHICLE_COLUMNS.map((column) => (
                <th
                  key={column.key}
                  className={column.key === "actions" ? "vehicle-actions-cell" : undefined}
                >
                  <span className="vehicle-resizable-heading">{column.label}</span>
                  <span
                    aria-hidden="true"
                    className="vehicle-column-resize-handle"
                    onMouseDown={(event) => handleColumnResizeStart(event, column)}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {safeItems.map((item) => {
              const isExpanded = expandedItemId === item.id;
              return (
                <Fragment key={item.id}>
                  <tr className={editingItemId === item.id ? "vehicle-row editing" : "vehicle-row"}>
                    <td>{formatText(item.company_name)}</td>
                    <td><strong>{item.vehicle_number}</strong></td>
                    <td className="vehicle-name-cell" title={formatText(item.vehicle_name)}>
                      {formatText(item.vehicle_name)}
                    </td>
                    <td>{formatText(item.driver_name)}</td>
                    <td><span className="software-type-badge">{formatText(item.ownership_type)}</span></td>
                    <td><InsuranceCompanyBadge company={item.insurance_company} /></td>
                    <td className="vehicle-insurance-type-cell" title={formatText(item.insurance_type)}>
                      {formatText(item.insurance_type)}
                    </td>
                    <td>{formatText(item.insurance_start_date)}</td>
                    <td>{formatText(item.insurance_end_date)}</td>
                    <td><DDayBadge dateValue={item.insurance_end_date} soonDays={30} /></td>
                    <td className="vehicle-detail-toggle-cell">
                      <button
                        type="button"
                        className="secondary-button software-action-button"
                        onClick={() => setExpandedItemId(isExpanded ? null : item.id)}
                      >
                        {isExpanded ? "리스 닫기" : "리스 상세"}
                      </button>
                    </td>
                    <td className="vehicle-actions-cell">
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
                  {isExpanded && (
                    <tr className="vehicle-detail-row">
                      <td colSpan="12">
                        <VehicleLeaseDetail item={item} onClose={() => setExpandedItemId(null)} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="vehicle-list-panel">
      <div className="software-list-controls vehicle-list-controls">
        <div className="vehicle-filter-group">
          <div className="software-tabs" aria-label="법인차량 회사 필터">
            {safeCompanyTabs.map((tab) => (
              <button
                type="button"
                key={tab.label}
                className={activeCompanyTab === tab.value ? "software-tab active" : "software-tab"}
                onClick={() => onCompanyTabChange(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="software-tabs" aria-label="법인차량 상태 필터">
            {safeTabs.map((tab) => (
              <button
                type="button"
                key={tab.label}
                className={activeTab === tab.value ? "software-tab active" : "software-tab"}
                onClick={() => onTabChange(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {renderContent()}
    </div>
  );
}

function InsuranceCompanyBadge({ company }) {
  const text = formatText(company);
  if (text === "-") {
    return text;
  }
  return (
    <span className={`vehicle-insurance-badge vehicle-insurance-${getInsuranceBadgeTone(text)}`}>
      {text}
    </span>
  );
}

function getInsuranceBadgeTone(company) {
  if (company.includes("삼성화재")) {
    return "samsung";
  }
  if (company.includes("KB손해보험")) {
    return "kb";
  }
  if (company.includes("DB손해보험")) {
    return "db";
  }
  return "default";
}

function VehicleLeaseDetail({ item, onClose }) {
  const details = [
    { label: "리스사", value: formatText(item.lease_company) },
    { label: "리스 시작일", value: formatText(item.lease_start_date) },
    { label: "리스 종료일", value: formatText(item.lease_end_date) },
    { label: "리스 D-Day", value: <DDayBadge dateValue={item.lease_end_date} soonDays={60} /> },
    { label: "월 리스금액", value: formatCurrency(item.monthly_lease_amount) },
    { label: "리스 납부일", value: formatText(item.lease_payment_day) },
    { label: "자동차세 및 기타", value: formatText(item.tax_note), wide: true },
  ];

  return (
    <div className="vehicle-detail-card">
      <div className="vehicle-detail-heading">
        <strong>{formatText(item.vehicle_number)} 리스 상세</strong>
        <button type="button" className="secondary-button software-action-button" onClick={onClose}>
          리스 닫기
        </button>
      </div>
      <dl className="vehicle-detail-grid">
        {details.map((detail) => (
          <div
            className={detail.wide ? "vehicle-detail-item vehicle-detail-item-wide" : "vehicle-detail-item"}
            key={detail.label}
          >
            <dt>{detail.label}</dt>
            <dd>{detail.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function DDayBadge({ dateValue, soonDays }) {
  const daysLeft = getDaysUntilDate(dateValue);
  const status = getDDayStatus(daysLeft, soonDays);
  return (
    <span className={`software-expiration-badge software-expiration-${status.tone}`}>
      {status.label}
    </span>
  );
}

function getDDayStatus(daysLeft, soonDays) {
  if (daysLeft === null) {
    return { label: "날짜 없음", tone: "muted" };
  }
  if (daysLeft < 0) {
    return { label: "만료됨", tone: "expired" };
  }
  return {
    label: `D-${daysLeft}`,
    tone: daysLeft <= soonDays ? "danger" : "normal",
  };
}

export function getDaysUntilDate(dateValue) {
  if (!dateValue) {
    return null;
  }

  const [year, month, day] = String(dateValue).split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const targetStart = new Date(year, month - 1, day);
  return Math.ceil((targetStart.getTime() - todayStart.getTime()) / 86400000);
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return Number(value || 0).toLocaleString("ko-KR");
}

function getInitialColumnWidths() {
  const defaultWidths = VEHICLE_COLUMNS.reduce(
    (widths, column) => ({ ...widths, [column.key]: column.initialWidth }),
    {},
  );

  if (typeof window === "undefined") {
    return defaultWidths;
  }

  try {
    const savedWidths = JSON.parse(window.localStorage.getItem(COLUMN_WIDTH_STORAGE_KEY) || "{}");
    return VEHICLE_COLUMNS.reduce((widths, column) => {
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

function saveColumnWidths(widths) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(COLUMN_WIDTH_STORAGE_KEY, JSON.stringify(widths));
  } catch {
    // Ignore storage failures; resizing still works for the current page state.
  }
}

export default VehicleList;
