import React from "react";

function ScmServerStatus({ status, isLoading, error, onRefresh }) {
  const tone = getStatusTone(status, error);
  const statusLabel = getStatusLabel(status, error);
  const uptime = formatUptime(status?.server_uptime_display || status?.uptime_display || status?.uptime_text);
  const mariadbTone = getMariaDbTone(status);
  const mariadbUptimeTone = getMariaDbUptimeTone(status);
  const mariadbUptimeBadge = getMariaDbUptimeBadge(status);
  const portTone = getPortTone(status);

  return (
    <section className="scm-status-grid" aria-label="SCM 서버 상태">
      <article className={`scm-status-card scm-status-card-${tone}`}>
        <span>연결 상태</span>
        <strong>{isLoading ? "확인 중" : statusLabel}</strong>
        <p>{error || status?.message || "SCM 서버 상태를 확인할 수 있습니다."}</p>
      </article>
      <article className="scm-status-card">
        <span>서버명</span>
        <strong>{status?.server_name || "SCM"}</strong>
        <p>내부 접속 정보는 화면에 표시하지 않습니다.</p>
      </article>
      <article className="scm-status-card scm-status-card-info">
        <span>서버 Uptime</span>
        <strong>{uptime.text}</strong>
        <p>SCM 서버 OS가 마지막 부팅 이후 실행된 시간입니다.</p>
      </article>
      <article className={`scm-status-card scm-status-card-${mariadbUptimeTone}`}>
        <div className="scm-card-title-row">
          <span>MariaDB 실행 시간</span>
          {mariadbUptimeBadge ? <em>{mariadbUptimeBadge}</em> : null}
        </div>
        <strong>{formatMariaDbUptime(status)}</strong>
        <p>MariaDB 서비스가 마지막 재시작 이후 실행된 시간입니다. 서버 Uptime과 다를 수 있습니다.</p>
        <small>시작 시각: {formatMariaDbActiveSince(status?.mariadb_active_since)}</small>
      </article>
      <article className={`scm-status-card scm-status-card-${mariadbTone}`}>
        <span>MariaDB 서비스 상태</span>
        <strong>{formatMariaDbStatus(status?.mariadb_status)}</strong>
        <p>{status?.mariadb_message || "MariaDB 서비스 상태를 확인합니다."}</p>
      </article>
      <article className={`scm-status-card scm-status-card-${portTone}`}>
        <span>3306 포트 상태</span>
        <strong>{formatPortStatus(status)}</strong>
        <p>{status?.db_port_message || "3306 포트 상태를 확인합니다."}</p>
      </article>
      <article className="scm-status-card">
        <span>마지막 확인</span>
        <strong>{formatDateTime(status?.checked_at)}</strong>
        <button type="button" className="secondary-button scm-refresh-button" onClick={onRefresh} disabled={isLoading}>
          {isLoading ? "확인 중" : "상태 새로고침"}
        </button>
      </article>
    </section>
  );
}

function getStatusTone(status, error) {
  if (error) {
    return "danger";
  }
  if (status?.status === "configuration_required") {
    return "warning";
  }
  if (status?.server_reachable || status?.reachable) {
    return "success";
  }
  if (status?.status === "connection_failed") {
    return "danger";
  }
  return "neutral";
}

function getStatusLabel(status, error) {
  if (error) {
    return "확인 실패";
  }
  if (status?.status === "configuration_required") {
    return "설정 필요";
  }
  if (status?.server_reachable || status?.reachable) {
    return "연결 가능";
  }
  if (status?.status === "connection_failed") {
    return "확인 실패";
  }
  return "상태 대기";
}

function getMariaDbTone(status) {
  if (status?.mariadb_status === "active" || status?.mariadb_active) {
    return "success";
  }
  if (status?.mariadb_status === "inactive" || status?.mariadb_status === "unknown") {
    return "warning";
  }
  if (status?.mariadb_status === "failed") {
    return "danger";
  }
  return "neutral";
}

function getMariaDbUptimeTone(status) {
  const days = Number(status?.mariadb_uptime_days);
  if (!Number.isFinite(days)) {
    return "neutral";
  }
  if (days >= 60) {
    return "danger-soft";
  }
  if (days >= 30) {
    return "warning";
  }
  return "success";
}

function getMariaDbUptimeBadge(status) {
  const days = Number(status?.mariadb_uptime_days);
  if (!Number.isFinite(days)) {
    return "";
  }
  if (days >= 60) {
    return "정기 점검 권장";
  }
  if (days >= 30) {
    return "장기 구동 중";
  }
  return "";
}

function getPortTone(status) {
  if (status?.db_port_reachable) {
    return "success";
  }
  if (status?.status === "configuration_required") {
    return "warning";
  }
  return "danger";
}

function formatMariaDbUptime(status) {
  return status?.mariadb_uptime_display || status?.mariadb_uptime_text || "-";
}

function formatMariaDbActiveSince(value) {
  if (!value) {
    return "-";
  }
  const sourceText = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(sourceText)) {
    return sourceText;
  }
  const date = new Date(sourceText);
  if (Number.isNaN(date.getTime())) {
    return sourceText;
  }
  return date
    .toLocaleString("sv-SE", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })
    .replace("T", " ");
}

function formatMariaDbStatus(status) {
  if (status === "active") {
    return "active";
  }
  if (status === "inactive") {
    return "inactive";
  }
  if (status === "failed") {
    return "failed";
  }
  return "unknown";
}

function formatPortStatus(status) {
  if (status?.db_port_reachable) {
    return "응답 가능";
  }
  if (status?.status === "configuration_required") {
    return "설정 필요";
  }
  return "응답 없음";
}

function formatDateTime(value) {
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
  });
}

function formatUptime(value) {
  if (!value) {
    return { text: "-", summary: "서버가 마지막 부팅 이후 계속 실행된 시간입니다." };
  }

  const sourceText = String(value).trim();
  const normalizedText = sourceText.replace(/^up\s+/i, "");
  const unitMap = {
    week: { label: "주", days: 7 },
    weeks: { label: "주", days: 7 },
    day: { label: "일", days: 1 },
    days: { label: "일", days: 1 },
    hour: { label: "시간", days: 0 },
    hours: { label: "시간", days: 0 },
    minute: { label: "분", days: 0 },
    minutes: { label: "분", days: 0 },
    second: { label: "초", days: 0 },
    seconds: { label: "초", days: 0 },
  };

  const parts = [];
  let approximateDays = 0;
  const matches = normalizedText.matchAll(/(\d+)\s+(weeks?|days?|hours?|minutes?|seconds?)/gi);
  for (const match of matches) {
    const amount = Number(match[1]);
    const unit = String(match[2]).toLowerCase();
    const unitInfo = unitMap[unit];
    if (!Number.isFinite(amount) || !unitInfo) {
      continue;
    }
    parts.push(`${amount}${unitInfo.label}`);
    approximateDays += amount * unitInfo.days;
  }

  if (parts.length === 0) {
    return { text: sourceText, summary: "서버가 마지막 부팅 이후 계속 실행된 시간입니다." };
  }

  return {
    text: parts.join(" "),
    summary:
      approximateDays > 0
        ? `약 ${approximateDays}일 동안 실행 중`
        : "서버가 마지막 부팅 이후 계속 실행된 시간입니다.",
  };
}

export default ScmServerStatus;
