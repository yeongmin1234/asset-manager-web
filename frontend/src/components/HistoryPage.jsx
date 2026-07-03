import React, { useEffect, useMemo, useState } from "react";
import { getActivityLogs } from "../api/client.js";
import useResizableColumns from "../hooks/useResizableColumns.js";
import {
  HISTORY_SORT_OPTIONS,
  SORT_VALUES,
  SortSelect,
  sortItems,
} from "../utils/sortOptions.jsx";

const HISTORY_FILTERS = [
  { label: "전체", targetType: "" },
  { label: "자산", targetType: "asset" },
  { label: "SW", targetType: "software" },
  { label: "법인차량", targetType: "vehicle" },
  { label: "보험 이력", targetType: "vehicle_insurance_history" },
  { label: "음료", targetType: "beverage_order" },
  { label: "설정", targetType: "admin_setting" },
];
const HISTORY_COLUMN_WIDTH_STORAGE_KEY = "assetManager.historyTable.columnWidths";
const HISTORY_COLUMNS = [
  { key: "createdAt", label: "일시", initialWidth: 150, minWidth: 120 },
  { key: "menu", label: "메뉴", initialWidth: 120, minWidth: 90 },
  { key: "action", label: "작업", initialWidth: 90, minWidth: 80 },
  { key: "target", label: "대상", initialWidth: 180, minWidth: 120 },
  { key: "summary", label: "요약", initialWidth: 300, minWidth: 160 },
  { key: "actor", label: "작업자/IP", initialWidth: 140, minWidth: 120 },
];

function HistoryPage() {
  const [logs, setLogs] = useState([]);
  const [activeFilter, setActiveFilter] = useState("");
  const [sortValue, setSortValue] = useState(SORT_VALUES.latest);
  const [state, setState] = useState({ isLoading: false, error: "" });
  const { columnWidths, handleColumnResizeStart, tableWidth } = useResizableColumns(
    HISTORY_COLUMNS,
    HISTORY_COLUMN_WIDTH_STORAGE_KEY,
    "history-column-resizing",
  );
  const displayedLogs = useMemo(
    () => sortItems(filterHistoryLogs(logs, activeFilter), sortValue, {
      created: ["created_at"],
    }),
    [activeFilter, logs, sortValue],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadLogs() {
      setState({ isLoading: true, error: "" });
      try {
        const data = await getActivityLogs({ limit: 100 });
        if (isMounted) {
          setLogs(Array.isArray(data) ? data : []);
          setState({ isLoading: false, error: "" });
        }
      } catch (error) {
        if (isMounted) {
          setLogs([]);
          setState({ isLoading: false, error: error.message });
        }
      }
    }

    loadLogs();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="content-panel history-page" aria-labelledby="history-page-title">
      <header className="history-header">
        <h2 id="history-page-title">변경 이력</h2>
        <p>자산, SW, 법인차량, 차량 보험 이력의 주요 작업 이력을 확인합니다.</p>
      </header>

      <div className="history-filter-tabs" aria-label="변경 이력 필터">
        {HISTORY_FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            aria-label={`${filter.label} 변경 이력 필터`}
            className={
              activeFilter === filter.targetType
                ? "history-filter-button history-filter-button-active"
                : "history-filter-button"
            }
            onClick={() => setActiveFilter(filter.targetType)}
          >
            <span className="history-filter-label">{filter.label}</span>
          </button>
        ))}
        <SortSelect
          value={sortValue}
          options={HISTORY_SORT_OPTIONS}
          onChange={setSortValue}
        />
      </div>

      <div className="history-list-panel">
        {state.isLoading && <div className="history-state">변경 이력을 불러오는 중입니다.</div>}

        {state.error && (
          <div className="history-state history-error">
            <span>{state.error}</span>
          </div>
        )}

        {!state.isLoading && !state.error && displayedLogs.length === 0 && (
          <div className="history-state">변경 이력이 없습니다.</div>
        )}

        {!state.isLoading && !state.error && displayedLogs.length > 0 && (
          <div className="history-table-wrap">
            <table className="history-table activity-history-table resizable-data-table" style={{ minWidth: `${tableWidth}px` }}>
              <colgroup>
                {HISTORY_COLUMNS.map((column) => (
                  <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
                ))}
              </colgroup>
              <thead>
                <tr>
                  {HISTORY_COLUMNS.map((column) => (
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
                {displayedLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{formatDateTime(log.created_at)}</td>
                    <td>{formatText(log.menu_name)}</td>
                    <td>
                      <span className={`history-action ${getActionClassName(log.action_type)}`}>
                        {getActionLabel(log.action_type)}
                      </span>
                    </td>
                    <td>{formatText(log.target_name || log.target_id)}</td>
                    <td>{formatText(log.summary)}</td>
                    <td>{formatText(log.actor_name || log.actor_ip)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

function filterHistoryLogs(logs, activeFilter) {
  const safeLogs = Array.isArray(logs) ? logs : [];
  if (!activeFilter) {
    return safeLogs;
  }
  return safeLogs.filter((log) => getHistoryLogType(log) === activeFilter);
}

function getHistoryLogType(log) {
  const haystack = [
    log?.menu_name,
    log?.target_type,
    log?.target_name,
    log?.summary,
    log?.description,
  ].filter(Boolean).join(" ").toLowerCase();

  if (haystack.includes("차량 보험 이력") || haystack.includes("보험 이력") || haystack.includes("vehicle_insurance")) {
    return "vehicle_insurance_history";
  }
  if (haystack.includes("법인차량") || haystack.includes("차량") || haystack.includes("vehicle")) {
    return "vehicle";
  }
  if (haystack.includes("software") || haystack.includes("sw") || haystack.includes("소프트웨어")) {
    return "software";
  }
  if (haystack.includes("음료") || haystack.includes("beverage")) {
    return "beverage_order";
  }
  if (haystack.includes("설정") || haystack.includes("admin") || haystack.includes("settings")) {
    return "admin_setting";
  }
  return "asset";
}

function getActionClassName(actionType) {
  const classMap = {
    create: "history-action-create",
    update: "history-action-update",
    delete: "history-action-delete",
    dispose: "history-action-delete",
    등록: "history-action-create",
    수정: "history-action-update",
    삭제: "history-action-delete",
    폐기: "history-action-delete",
  };
  return classMap[actionType] || "history-action-unknown";
}

function getActionLabel(actionType) {
  const labelMap = {
    create: "등록",
    update: "수정",
    delete: "삭제",
    dispose: "폐기",
  };
  return labelMap[actionType] || formatText(actionType);
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default HistoryPage;
