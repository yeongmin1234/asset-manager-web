import React, { useEffect, useState } from "react";
import { getRecentActivityLogs } from "../api/client.js";

function RecentActivityPanel({ onNavigate }) {
  const [logs, setLogs] = useState([]);
  const [state, setState] = useState({ isLoading: false, error: "" });

  useEffect(() => {
    let isMounted = true;

    async function loadRecentLogs() {
      setState({ isLoading: true, error: "" });
      try {
        const data = await getRecentActivityLogs(5);
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

    loadRecentLogs();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="portal-side-card" id="activity" aria-labelledby="recent-activity-title">
      <div className="side-card-heading">
        <h3 id="recent-activity-title">최근 변경 이력</h3>
        <button type="button" className="link-button" onClick={() => onNavigate?.("history")}>
          더보기
        </button>
      </div>

      {state.isLoading ? (
        <div className="recent-empty">
          <strong>불러오는 중입니다.</strong>
          <span>최근 변경 이력을 확인하고 있습니다.</span>
        </div>
      ) : state.error ? (
        <div className="recent-empty">
          <strong>이력을 불러오지 못했습니다.</strong>
          <span>{state.error}</span>
        </div>
      ) : logs.length === 0 ? (
        <div className="recent-empty">
          <strong>최근 활동이 없습니다.</strong>
          <span>업무 변경 후 표시됩니다.</span>
        </div>
      ) : (
        <div className="recent-activity-list">
          {logs.map((log) => (
            <div className="recent-activity-item" key={log.id}>
              <span className="activity-dot" />
              <div>
                <strong>[{formatText(log.menu_name)}] {formatText(log.action_type)}</strong>
                <p>{formatText(log.summary || log.target_name)} · {formatDateTime(log.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
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
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default RecentActivityPanel;
