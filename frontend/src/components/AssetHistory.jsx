import React, { useEffect, useMemo, useState } from "react";
import { getAssetHistory } from "../api/client.js";

const ACTION_LABELS = {
  등록: "등록",
  수정: "수정",
  상태변경: "상태변경",
  폐기: "폐기",
  삭제: "삭제",
};

function AssetHistory({ assetId, refreshKey }) {
  const [histories, setHistories] = useState([]);
  const [historyState, setHistoryState] = useState({ isLoading: false, error: "" });

  useEffect(() => {
    if (!assetId) {
      setHistories([]);
      setHistoryState({ isLoading: false, error: "" });
      return;
    }

    let ignore = false;

    async function loadHistory() {
      setHistoryState({ isLoading: true, error: "" });
      try {
        const data = await getAssetHistory(assetId);
        if (!ignore) {
          setHistories(sortHistories(Array.isArray(data) ? data : []));
          setHistoryState({ isLoading: false, error: "" });
        }
      } catch (error) {
        if (!ignore) {
          setHistories([]);
          setHistoryState({ isLoading: false, error: error.message });
        }
      }
    }

    loadHistory();

    return () => {
      ignore = true;
    };
  }, [assetId, refreshKey]);

  const safeHistories = useMemo(() => sortHistories(histories), [histories]);

  return (
    <section className="history-section" aria-labelledby="asset-history-title">
      <div className="history-heading">
        <div>
          <p className="eyebrow">History</p>
          <h3 id="asset-history-title">변경 이력</h3>
        </div>
      </div>

      {historyState.isLoading && (
        <div className="history-state">변경 이력을 불러오는 중입니다.</div>
      )}

      {historyState.error && (
        <div className="history-state history-error">
          <strong>변경 이력을 불러오지 못했습니다.</strong>
          <span>{historyState.error}</span>
        </div>
      )}

      {!historyState.isLoading && !historyState.error && safeHistories.length === 0 && (
        <div className="history-state">변경 이력이 없습니다.</div>
      )}

      {!historyState.isLoading && !historyState.error && safeHistories.length > 0 && (
        <div className="history-table-wrap">
          <table className="history-table">
            <thead>
              <tr>
                <th>작업유형</th>
                <th>변경 항목</th>
                <th>이전 값</th>
                <th>변경 값</th>
                <th>메모</th>
                <th>변경일시</th>
              </tr>
            </thead>
            <tbody>
              {safeHistories.map((history) => (
                <tr key={history.id}>
                  <td>
                    <span className={`history-action history-action-${getActionClass(history.action_type)}`}>
                      {ACTION_LABELS[history.action_type] || history.action_type || "-"}
                    </span>
                  </td>
                  <td>{formatText(history.field_name)}</td>
                  <td>{formatText(history.old_value)}</td>
                  <td>{formatText(history.new_value)}</td>
                  <td>{formatText(history.memo)}</td>
                  <td>{formatDateTime(history.changed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function sortHistories(items) {
  return [...items].sort((left, right) => {
    const leftTime = new Date(left.changed_at || 0).getTime();
    const rightTime = new Date(right.changed_at || 0).getTime();
    return rightTime - leftTime || (right.id || 0) - (left.id || 0);
  });
}

function getActionClass(actionType) {
  const classMap = {
    등록: "create",
    수정: "update",
    상태변경: "status",
    폐기: "dispose",
    삭제: "delete",
  };
  return classMap[actionType] || "unknown";
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
    return value;
  }
  return date.toLocaleString("ko-KR");
}

export default AssetHistory;
