import React from "react";

const EMPTY_SUMMARY = {
  total_assets: 0,
  in_use_assets: 0,
  unused_assets: 0,
  disposed_assets: 0,
  total_purchase_amount: 0,
};

function StatsSummary({ summary, isLoading, error }) {
  const safeSummary = { ...EMPTY_SUMMARY, ...(summary || {}) };
  const cards = [
    { label: "전체 자산", value: formatCount(safeSummary.total_assets), icon: "▦", tone: "blue" },
    { label: "사용중", value: formatCount(safeSummary.in_use_assets), icon: "✓", tone: "green" },
    { label: "미사용", value: formatCount(safeSummary.unused_assets), icon: "Ⅱ", tone: "amber" },
    { label: "폐기", value: formatCount(safeSummary.disposed_assets), icon: "⌫", tone: "red" },
  ];

  return (
    <section className="stats-summary" aria-labelledby="stats-summary-title">
      <h3 id="stats-summary-title" className="stats-summary-compact-title">자산 현황</h3>
      {isLoading && <span className="inline-info">통계를 불러오는 중입니다.</span>}
      {error && !isLoading && (
        <span className="inline-alert">자산 현황을 불러오지 못했습니다.</span>
      )}
      {error && !isLoading && <p className="state-detail">{error}</p>}

      <div className="stats-grid">
        {cards.map((card) => (
          <div
            className={`stats-card stats-card-${card.tone}`}
            key={card.label}
          >
            <div>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
            </div>
            <span className="stats-card-icon" aria-hidden="true">{card.icon}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatCount(value) {
  return `${Number(value || 0).toLocaleString("ko-KR")}개`;
}

export default StatsSummary;
