import React, { useEffect, useRef } from "react";

function formatCheckedAt(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function formatLastSeen(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function shortenUserAgent(value) {
  const text = String(value || "");
  if (!text) {
    return "-";
  }
  if (text.includes("Edg/")) {
    return "Edge";
  }
  if (text.includes("Chrome/")) {
    return "Chrome";
  }
  if (text.includes("Firefox/")) {
    return "Firefox";
  }
  if (text.includes("Safari/")) {
    return "Safari";
  }
  return text.slice(0, 32);
}

function getVisitorDisplayName(visitor) {
  return visitor?.user_name || visitor?.username || visitor?.ip_address || "알 수 없음";
}

function getVisitorMeta(visitor) {
  const lastSeen = formatLastSeen(visitor?.last_seen);
  if (visitor?.user_name || visitor?.username) {
    return `${visitor?.ip_address || "-"} · ${lastSeen}`;
  }
  return lastSeen;
}

function StatusValue({ isOk, unknownLabel = "확인 대기" }) {
  if (isOk === null || isOk === undefined) {
    return (
      <span className="server-status-value server-status-value-idle">
        <span aria-hidden="true" />
        {unknownLabel}
      </span>
    );
  }

  return (
    <span className={`server-status-value ${isOk ? "server-status-value-ok" : "server-status-value-error"}`}>
      <span aria-hidden="true" />
      {isOk ? "정상" : "오류"}
    </span>
  );
}

function getStatusButtonClass(status) {
  if (status?.isLoading) {
    return "server-status-button-checking";
  }
  if (status?.type === "ok") {
    return "server-status-button-ok";
  }
  if (status?.type === "error" || status?.type === "warning") {
    return "server-status-button-error";
  }
  return "server-status-button-idle";
}

function ServerStatusPopover({
  isOpen,
  onToggle,
  onClose,
  onCheck,
  showVisitorSummary = false,
  status,
  visitorSummary,
}) {
  const wrapperRef = useRef(null);
  const activeCount = showVisitorSummary ? visitorSummary?.active_count : null;
  const visitors = Array.isArray(visitorSummary?.visitors) ? visitorSummary.visitors : [];

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (!wrapperRef.current?.contains(event.target)) {
        onClose?.();
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  const backendOk = status?.backendOk ?? (status?.type === "ok" || status?.type === "warning" ? true : null);
  const dbOk = status?.dbOk ?? (status?.type === "ok" ? true : status?.type === "warning" ? false : null);
  const hasError = status?.type === "error" || status?.type === "warning";

  return (
    <div className="server-status-control" ref={wrapperRef}>
      <button
        type="button"
        className={`server-status-button ${getStatusButtonClass(status)}`}
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <span className="server-status-button-dot" aria-hidden="true" />
        {status?.isLoading
          ? "확인 중..."
          : activeCount === null || activeCount === undefined
            ? "서버 상태"
            : `현재 접속 ${activeCount}명`}
      </button>

      {isOpen ? (
        <div className="server-status-popover" role="dialog" aria-label="서버 상태">
          <div className="server-status-popover-header">
            <div>
              <h3>서버 상태</h3>
              <p>{status?.isLoading ? "상태를 확인 중입니다." : "현재 연결 상태입니다."}</p>
            </div>
          </div>

          <dl className="server-status-list">
            <div>
              <dt>Backend API</dt>
              <dd>
                {status?.isLoading ? (
                  <span className="server-status-value server-status-value-idle">
                    <span aria-hidden="true" />
                    확인 중...
                  </span>
                ) : (
                  <StatusValue isOk={backendOk} />
                )}
              </dd>
            </div>
            <div>
              <dt>DB 연결</dt>
              <dd>
                {status?.isLoading ? (
                  <span className="server-status-value server-status-value-idle">
                    <span aria-hidden="true" />
                    확인 중...
                  </span>
                ) : (
                  <StatusValue isOk={dbOk} />
                )}
              </dd>
            </div>
            <div>
              <dt>Frontend</dt>
              <dd>
                <span className="server-status-value server-status-value-ok">
                  <span aria-hidden="true" />
                  실행 중
                </span>
              </dd>
            </div>
            <div>
              <dt>마지막 확인</dt>
              <dd>{status?.isLoading ? "확인 중..." : formatCheckedAt(status?.checkedAt)}</dd>
            </div>
          </dl>

          {hasError && status?.message ? (
            <p className="server-status-error">{status.message}</p>
          ) : null}

          {showVisitorSummary ? <div className="visitor-summary">
            <div className="visitor-summary-heading">
              <strong>접속자 현황</strong>
              <span>최근 {visitorSummary?.active_window_seconds || 180}초 기준</span>
            </div>
            {visitorSummary?.error ? (
              <p className="visitor-summary-error">접속자 현황을 불러오지 못했습니다.</p>
            ) : visitors.length > 0 ? (
              <div className="visitor-list">
                {visitors.map((visitor) => (
                  <div className="visitor-item" key={visitor.ip_address}>
                    <strong>{getVisitorDisplayName(visitor)}</strong>
                    <span className="visitor-browser">{shortenUserAgent(visitor.user_agent)}</span>
                    <span className="visitor-meta">{getVisitorMeta(visitor)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="visitor-summary-empty">현재 접속 정보를 확인 중입니다.</p>
            )}
          </div> : null}

          <button
            type="button"
            className="btn btn-secondary server-status-refresh"
            onClick={onCheck}
            disabled={status?.isLoading}
          >
            {status?.isLoading ? "확인 중..." : "다시 확인"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default ServerStatusPopover;
