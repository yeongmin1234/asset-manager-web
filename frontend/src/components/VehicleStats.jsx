import React from "react";

const INITIAL_SUMMARY = {
  total_vehicles: 0,
  company_owned_count: 0,
  lease_count: 0,
  expiring_soon_count: 0,
};

function VehicleStats({
  summary,
  isLoading,
  error,
  recentInsuranceHistories = [],
  onRecentInsuranceSelect,
  compact = false,
}) {
  const safeSummary = { ...INITIAL_SUMMARY, ...(summary || {}) };
  const safeRecentInsuranceHistories = Array.isArray(recentInsuranceHistories)
    ? recentInsuranceHistories.slice(0, 3)
    : [];
  const cards = [
    { label: "전체 차량", value: safeSummary.total_vehicles, tone: "blue" },
    { label: "회사 소유", value: safeSummary.company_owned_count, tone: "green" },
    { label: "리스", value: safeSummary.lease_count, tone: "purple" },
    { label: "만기 임박", value: safeSummary.expiring_soon_count, tone: "amber" },
  ];

  return (
    <section
      className={compact ? "vehicle-stats vehicle-stats-compact" : "stats-summary vehicle-stats"}
      aria-labelledby={compact ? undefined : "vehicle-stats-title"}
      aria-label={compact ? "차량 요약" : undefined}
    >
      {!compact && (
        <div className="section-heading">
          <div>
            <h2 id="vehicle-stats-title">차량 요약</h2>
            <p>소유권과 보험/리스 만기 임박 차량을 확인합니다.</p>
          </div>
          {isLoading && <span className="status-pill">집계 중</span>}
          {error && <span className="lookup-warning">{error}</span>}
        </div>
      )}
      {compact && (isLoading || error) && (
        <div className="vehicle-stats-note">
          {isLoading && <span className="status-pill">집계 중</span>}
          {error && <span className="lookup-warning">{error}</span>}
        </div>
      )}
      <div className="stats-grid">
        {cards.map((card) => (
          <article className={`stats-card stats-card-${card.tone}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{Number(card.value || 0).toLocaleString("ko-KR")}</strong>
          </article>
        ))}
        {compact && (
          <article className="stats-card vehicle-recent-insurance-card">
            <div className="vehicle-recent-insurance-heading">
              <span>최근 보험 이력</span>
              <strong>{safeRecentInsuranceHistories.length}</strong>
            </div>
            {safeRecentInsuranceHistories.length === 0 ? (
              <p className="vehicle-recent-insurance-empty">최근 보험 이력이 없습니다.</p>
            ) : (
              <div className="vehicle-recent-insurance-list">
                {safeRecentInsuranceHistories.map((history) => (
                  <button
                    type="button"
                    className="vehicle-recent-insurance-item"
                    key={`${history.vehicle_id || history.vehicle?.id || "vehicle"}-${history.id}`}
                    onClick={() => onRecentInsuranceSelect?.(history)}
                  >
                    <span className="vehicle-recent-insurance-main">
                      <strong>{formatText(history.vehicle?.vehicle_number)}</strong>
                      <em>{formatText(history.vehicle?.vehicle_name || history.driver_name)}</em>
                    </span>
                    <span className="vehicle-recent-insurance-meta">
                      {formatPeriod(history.start_date, history.end_date)}
                    </span>
                    <span className="vehicle-recent-insurance-meta">
                      {formatText(history.insurance_type || formatCurrency(history.amount))}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </article>
        )}
      </div>
    </section>
  );
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatPeriod(startDate, endDate) {
  return `${formatText(startDate)} ~ ${formatText(endDate)}`;
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return `${Number(value || 0).toLocaleString("ko-KR")}원`;
}

export default VehicleStats;
