import React, { useCallback, useEffect, useMemo, useState } from "react";
import { getNetworkStatus } from "../api/client.js";

const EMPTY_SUMMARY = {
  total: 0,
  ok: 0,
  warning: 0,
  down: 0,
};

const STATUS_LABELS = {
  ok: "정상",
  warning: "주의",
  down: "장애",
};

const TYPE_LABELS = {
  http: "HTTP",
  tcp: "TCP",
};

function NetworkStatusPage() {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [statusState, setStatusState] = useState({ isLoading: false, error: "" });

  const loadStatus = useCallback(async () => {
    setStatusState({ isLoading: true, error: "" });
    try {
      const data = await getNetworkStatus();
      setItems(Array.isArray(data?.items) ? data.items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(data?.summary || {}) });
      setStatusState({ isLoading: false, error: "" });
    } catch (error) {
      setItems([]);
      setSummary(EMPTY_SUMMARY);
      setStatusState({ isLoading: false, error: error.message });
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const summaryCards = useMemo(
    () => [
      { label: "전체", value: summary.total, tone: "neutral" },
      { label: "정상", value: summary.ok, tone: "ok" },
      { label: "주의", value: summary.warning, tone: "warning" },
      { label: "장애", value: summary.down, tone: "down" },
    ],
    [summary],
  );

  return (
    <>
      <div className="portal-screen-heading network-status-heading">
        <div>
          <h2>네트워크 현황</h2>
          <p>사내 주요 네트워크 서비스와 서버 상태를 확인합니다.</p>
        </div>
        <button
          type="button"
          className="primary-button network-refresh-button"
          onClick={loadStatus}
          disabled={statusState.isLoading}
        >
          {statusState.isLoading ? "확인 중" : "새로고침"}
        </button>
      </div>

      <section className="network-summary-grid" aria-label="네트워크 상태 요약">
        {summaryCards.map((card) => (
          <article className={`network-summary-card network-summary-card-${card.tone}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </section>

      <section className="content-panel network-status-panel">
        <div className="section-heading network-panel-heading">
          <div>
            <h3>상태 체크</h3>
            <p>TCP/HTTP 연결만 확인하며 설정 변경이나 로그인을 수행하지 않습니다.</p>
          </div>
        </div>

        {statusState.error ? (
          <div className="empty-state error-state">네트워크 상태를 불러오지 못했습니다. {statusState.error}</div>
        ) : null}

        {!statusState.error && statusState.isLoading && items.length === 0 ? (
          <div className="empty-state">네트워크 상태를 확인 중입니다.</div>
        ) : null}

        {!statusState.error && !statusState.isLoading && items.length === 0 ? (
          <div className="empty-state">표시할 네트워크 상태가 없습니다.</div>
        ) : null}

        {items.length > 0 ? (
          <div className="table-scroll network-table-scroll">
            <table className="data-table network-status-table">
              <thead>
                <tr>
                  <th>서비스명</th>
                  <th>대상</th>
                  <th>유형</th>
                  <th>상태</th>
                  <th>응답시간</th>
                  <th>마지막 확인 시간</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={`${item.name}-${item.target}`}>
                    <td className="network-service-name">{displayValue(item.name)}</td>
                    <td className="network-target" title={displayValue(item.target)}>
                      {displayValue(item.target)}
                    </td>
                    <td>{TYPE_LABELS[item.type] || displayValue(item.type)}</td>
                    <td>
                      <span className={`network-status-badge network-status-badge-${normalizeStatus(item.status)}`}>
                        {STATUS_LABELS[normalizeStatus(item.status)] || displayValue(item.status)}
                      </span>
                    </td>
                    <td>{formatLatency(item.latency_ms)}</td>
                    <td>{formatCheckedAt(item.checked_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </>
  );
}

function normalizeStatus(status) {
  if (status === "ok" || status === "warning" || status === "down") {
    return status;
  }
  return "down";
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatLatency(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }
  return `${numericValue}ms`;
}

function formatCheckedAt(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default NetworkStatusPage;
