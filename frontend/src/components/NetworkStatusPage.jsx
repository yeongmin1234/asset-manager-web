import React, { useCallback, useEffect, useMemo, useState } from "react";
import { getNetworkStatus } from "../api/client.js";
import NetworkCredentialPage from "./NetworkCredentialPage.jsx";
import {
  ASSET_SORT_OPTIONS,
  SORT_VALUES,
  SortSelect,
  sortItems,
} from "../utils/sortOptions.jsx";

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
  const [activeTab, setActiveTab] = useState("devices");

  return (
    <>
      <div className="portal-screen-heading network-status-heading">
        <div>
          <h2>네트워크 현황</h2>
          <p>사내 네트워크 장비 상태와 접속정보를 관리합니다.</p>
        </div>
      </div>

      <div className="network-page-tabs" role="tablist" aria-label="네트워크 현황 탭">
        <button
          type="button"
          className={activeTab === "devices" ? "network-page-tab active" : "network-page-tab"}
          role="tab"
          aria-selected={activeTab === "devices"}
          onClick={() => setActiveTab("devices")}
        >
          장비 현황
        </button>
        <button
          type="button"
          className={activeTab === "credentials" ? "network-page-tab active" : "network-page-tab"}
          role="tab"
          aria-selected={activeTab === "credentials"}
          onClick={() => setActiveTab("credentials")}
        >
          접속정보 관리
        </button>
      </div>

      {activeTab === "devices" ? <NetworkDeviceStatusPanel /> : <NetworkCredentialPage />}
    </>
  );
}

function NetworkDeviceStatusPanel() {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [publicIp, setPublicIp] = useState(null);
  const [recentChecks, setRecentChecks] = useState([]);
  const [statusState, setStatusState] = useState({ isLoading: false, error: "", requestUrl: "" });
  const [isAutoRefreshEnabled, setIsAutoRefreshEnabled] = useState(false);
  const [sortValue, setSortValue] = useState(SORT_VALUES.latest);

  const loadStatus = useCallback(async () => {
    setStatusState((currentState) => ({ ...currentState, isLoading: true, error: "", requestUrl: "" }));
    try {
      const data = await getNetworkStatus();
      setItems(Array.isArray(data?.items) ? data.items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(data?.summary || {}) });
      setPublicIp(data?.public_ip || null);
      setRecentChecks(Array.isArray(data?.recent_checks) ? data.recent_checks : []);
      setStatusState({ isLoading: false, error: "", requestUrl: "" });
    } catch (error) {
      setItems([]);
      setSummary(EMPTY_SUMMARY);
      setPublicIp(null);
      setRecentChecks([]);
      setStatusState({
        isLoading: false,
        error: error.message || "네트워크 상태를 불러오지 못했습니다.",
        requestUrl: error.url || "",
      });
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!isAutoRefreshEnabled) {
      return undefined;
    }

    const intervalId = window.setInterval(loadStatus, 60000);
    return () => window.clearInterval(intervalId);
  }, [isAutoRefreshEnabled, loadStatus]);

  const summaryCards = useMemo(
    () => [
      { label: "전체", value: summary.total, tone: "neutral" },
      { label: "정상", value: summary.ok, tone: "ok" },
      { label: "주의", value: summary.warning, tone: "warning" },
      { label: "장애", value: summary.down, tone: "down" },
    ],
    [summary],
  );

  const displayedItems = useMemo(
    () => sortItems(items, sortValue, {
      created: ["checked_at"],
      updated: ["checked_at", "last_problem_at"],
      name: ["name", "target"],
    }),
    [items, sortValue],
  );

  return (
    <>
      <div className="network-device-toolbar">
        <div>
          <h3>장비 현황</h3>
          <p>사내 주요 네트워크 서비스와 서버 상태를 확인합니다.</p>
        </div>
        <button
          type="button"
          className="secondary-button network-refresh-button"
          onClick={loadStatus}
          disabled={statusState.isLoading}
        >
          {statusState.isLoading ? "확인 중" : "새로고침"}
        </button>
        <SortSelect
          value={sortValue}
          options={ASSET_SORT_OPTIONS}
          onChange={setSortValue}
        />
      </div>

      <section className="network-summary-compact" aria-label="네트워크 상태 요약">
        <article className="network-summary-chip network-summary-chip-public-ip">
          <span>공인 IP</span>
          <strong>{publicIp || "확인 실패"}</strong>
        </article>
        {summaryCards.map((card) => (
          <article className={`network-summary-chip network-summary-chip-${card.tone}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
        <label className="network-auto-refresh-toggle">
          <input
            type="checkbox"
            checked={isAutoRefreshEnabled}
            onChange={(event) => setIsAutoRefreshEnabled(event.target.checked)}
          />
          <span>자동 새로고침 60초</span>
        </label>
      </section>

      <section className="content-panel network-status-panel">
        <div className="section-heading network-panel-heading">
          <div>
            <h3>상태 체크</h3>
            <p>TCP/HTTP 연결만 확인하며 설정 변경이나 로그인을 수행하지 않습니다.</p>
          </div>
        </div>

        {statusState.error ? (
          <div className="empty-state error-state">
            네트워크 상태를 불러오지 못했습니다. {statusState.error}
            {statusState.requestUrl ? (
              <small>요청 URL: {statusState.requestUrl}</small>
            ) : null}
          </div>
        ) : null}

        {!statusState.error && statusState.isLoading && displayedItems.length === 0 ? (
          <div className="empty-state">네트워크 상태를 확인 중입니다.</div>
        ) : null}

        {!statusState.error && !statusState.isLoading && displayedItems.length === 0 ? (
          <div className="empty-state">표시할 네트워크 상태가 없습니다.</div>
        ) : null}

        {displayedItems.length > 0 ? (
          <div className="table-scroll network-table-scroll">
            <table className="data-table network-status-table">
              <thead>
                <tr>
                  <th>서비스명</th>
                  <th>대상</th>
                  <th>유형</th>
                  <th>상태</th>
                  <th>응답시간</th>
                  <th>마지막 확인</th>
                </tr>
              </thead>
              <tbody>
                {displayedItems.map((item) => (
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
                      {item.last_problem_at ? (
                        <small className="network-status-note">
                          최근 문제 {formatCompactTime(item.last_problem_at)}
                        </small>
                      ) : null}
                    </td>
                    <td>{formatLatency(item.latency_ms)}</td>
                    <td>{formatCheckedAt(item.checked_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {recentChecks.length > 0 ? (
          <div className="network-recent-checks">
            <strong>최근 상태 이력</strong>
            <ul>
              {recentChecks.slice(0, 10).map((check, index) => (
                <li key={`${check.checked_at}-${index}`}>
                  <span>{formatCompactTime(check.checked_at)}</span>
                  <span>정상 {displayValue(check.ok)}</span>
                  <span>주의 {displayValue(check.warning)}</span>
                  <span>장애 {displayValue(check.down)}</span>
                </li>
              ))}
            </ul>
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

function formatCompactTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default NetworkStatusPage;
