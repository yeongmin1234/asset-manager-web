import React, { useEffect, useState } from "react";
import { getActivityLogs } from "../api/client.js";

const HISTORY_FILTERS = [
  { label: "전체", targetType: "" },
  { label: "자산", targetType: "asset" },
  { label: "SW", targetType: "software" },
  { label: "법인차량", targetType: "vehicle" },
  { label: "보험 이력", targetType: "vehicle_insurance_history" },
];

function HistoryPage() {
  const [logs, setLogs] = useState([]);
  const [activeFilter, setActiveFilter] = useState("");
  const [state, setState] = useState({ isLoading: false, error: "" });

  useEffect(() => {
    let isMounted = true;

    async function loadLogs() {
      setState({ isLoading: true, error: "" });
      try {
        const data = await getActivityLogs({ target_type: activeFilter });
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
  }, [activeFilter]);

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
      </div>

      <div className="history-list-panel">
        {state.isLoading && <div className="history-state">변경 이력을 불러오는 중입니다.</div>}

        {state.error && (
          <div className="history-state history-error">
            <span>{state.error}</span>
          </div>
        )}

        {!state.isLoading && !state.error && logs.length === 0 && (
          <div className="history-state">변경 이력이 없습니다.</div>
        )}

        {!state.isLoading && !state.error && logs.length > 0 && (
          <div className="history-table-wrap">
            <table className="history-table activity-history-table">
              <thead>
                <tr>
                  <th>일시</th>
                  <th>메뉴</th>
                  <th>작업</th>
                  <th>대상</th>
                  <th>요약</th>
                  <th>작업자/IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
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
