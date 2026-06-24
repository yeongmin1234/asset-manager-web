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
  isRecentInsuranceOpen = false,
  onRecentInsuranceOpen,
  onRecentInsuranceClose,
  onRecentInsuranceSelect,
  compact = false,
}) {
  const safeSummary = { ...INITIAL_SUMMARY, ...(summary || {}) };
  const safeRecentInsuranceHistories = Array.isArray(recentInsuranceHistories)
    ? recentInsuranceHistories.slice(0, 5)
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
          <button
            type="button"
            className="stats-card vehicle-recent-insurance-card"
            onClick={onRecentInsuranceOpen}
          >
            <span>최근 보험 이력</span>
            <strong>{safeRecentInsuranceHistories.length}</strong>
            <small>클릭해서 최근 등록 내역 보기</small>
          </button>
        )}
      </div>
      {compact && (
        <VehicleRecentInsuranceModal
          histories={safeRecentInsuranceHistories}
          isOpen={isRecentInsuranceOpen}
          onClose={onRecentInsuranceClose}
          onSelect={onRecentInsuranceSelect}
        />
      )}
    </section>
  );
}

function VehicleRecentInsuranceModal({ histories, isOpen, onClose, onSelect }) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="vehicle-recent-insurance-modal-backdrop" role="presentation">
      <section
        className="vehicle-recent-insurance-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="vehicle-recent-insurance-title"
      >
        <div className="vehicle-recent-insurance-modal-heading">
          <div>
            <h3 id="vehicle-recent-insurance-title">최근 보험 이력</h3>
            <p>최근 등록 또는 수정된 보험 이력을 확인합니다.</p>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>
            닫기
          </button>
        </div>
        {histories.length === 0 ? (
          <div className="state-panel vehicle-recent-insurance-empty">
            최근 보험 이력이 없습니다.
          </div>
        ) : (
          <div className="vehicle-recent-insurance-modal-list">
            {histories.map((history) => (
              <button
                type="button"
                className="vehicle-recent-insurance-modal-item"
                key={`${history.vehicle_id || history.vehicle?.id || "vehicle"}-${history.id}`}
                onClick={() => onSelect?.(history)}
              >
                <span className="vehicle-recent-insurance-main">
                  <strong>{formatText(history.vehicle?.vehicle_number)}</strong>
                  <em>{formatText(history.vehicle?.vehicle_name)}</em>
                </span>
                <span>{formatPeriod(history.start_date, history.end_date)}</span>
                <span>{formatText(history.insurance_type || formatCurrency(history.amount))}</span>
                <small>{formatDateTime(history.created_at || history.updated_at)}</small>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
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

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return formatText(value);
  }
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default VehicleStats;
