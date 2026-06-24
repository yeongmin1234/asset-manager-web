import React from "react";

function ScmServerStatus({ status, isLoading, error, onRefresh }) {
  const tone = getStatusTone(status, error);
  const statusLabel = getStatusLabel(status, error);
  const uptime = formatUptime(status?.uptime_text);

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
      <article className="scm-status-card">
        <span>Uptime</span>
        <strong>{uptime.text}</strong>
        <p>{uptime.summary || "서버가 마지막 부팅 이후 계속 실행된 시간입니다."}</p>
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
  if (status?.reachable) {
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
  if (status?.reachable) {
    return "연결 가능";
  }
  if (status?.status === "connection_failed") {
    return "확인 실패";
  }
  return "상태 대기";
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
