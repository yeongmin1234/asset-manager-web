import React from "react";

const INITIAL_SUMMARY = {
  total_vehicles: 0,
  company_owned_count: 0,
  lease_count: 0,
  expiring_soon_count: 0,
};

function VehicleStats({ summary, isLoading, error }) {
  const safeSummary = { ...INITIAL_SUMMARY, ...(summary || {}) };
  const cards = [
    { label: "전체 차량", value: safeSummary.total_vehicles, tone: "blue" },
    { label: "회사 소유", value: safeSummary.company_owned_count, tone: "green" },
    { label: "리스", value: safeSummary.lease_count, tone: "purple" },
    { label: "만기 임박", value: safeSummary.expiring_soon_count, tone: "amber" },
  ];

  return (
    <section className="stats-summary vehicle-stats" aria-labelledby="vehicle-stats-title">
      <div className="section-heading">
        <div>
          <h2 id="vehicle-stats-title">차량 요약</h2>
          <p>소유권과 보험/리스 만기 임박 차량을 확인합니다.</p>
        </div>
        {isLoading && <span className="status-pill">집계 중</span>}
        {error && <span className="lookup-warning">{error}</span>}
      </div>
      <div className="stats-grid">
        {cards.map((card) => (
          <article className={`stats-card stats-card-${card.tone}`} key={card.label}>
            <span>{card.label}</span>
            <strong>{Number(card.value || 0).toLocaleString("ko-KR")}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}

export default VehicleStats;
