import React, { useEffect, useState } from "react";
import { getActivityLogs } from "../api/client.js";

function HistoryPage() {
  const [logs, setLogs] = useState([]);
  const [state, setState] = useState({ isLoading: false, error: "" });

  useEffect(() => {
    let isMounted = true;

    async function loadLogs() {
      setState({ isLoading: true, error: "" });
      try {
        const data = await getActivityLogs();
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
      <div className="section-heading">
        <div>
          <h2 id="history-page-title">변경 이력</h2>
          <p>자산 및 SW 현황의 주요 작업 이력을 확인합니다.</p>
        </div>
      </div>

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
                <th>메뉴</th>
                <th>작업</th>
                <th>대상 유형</th>
                <th>대상</th>
                <th>작업자</th>
                <th>시간</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{formatText(log.menu_name)}</td>
                  <td>
                    <span className={`history-action ${getActionClassName(log.action_type)}`}>
                      {formatText(log.action_type)}
                    </span>
                  </td>
                  <td>{getTargetTypeLabel(log.target_type)}</td>
                  <td>{formatText(log.target_name || log.target_id)}</td>
                  <td>{formatText(log.actor_name || log.actor_ip)}</td>
                  <td>{formatDateTime(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function getActionClassName(actionType) {
  const classMap = {
    등록: "history-action-create",
    수정: "history-action-update",
    삭제: "history-action-delete",
  };
  return classMap[actionType] || "history-action-unknown";
}

function getTargetTypeLabel(targetType) {
  const labelMap = {
    software: "SW",
  };
  return labelMap[targetType] || formatText(targetType);
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
