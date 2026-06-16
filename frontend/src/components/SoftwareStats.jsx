import React from "react";

const EMPTY_STATS = {
  total_software: 0,
  perpetual_count: 0,
  subscription_count: 0,
  discontinued_count: 0,
};

function SoftwareStats({ summary, expirationSummary, isLoading, error }) {
  const safeSummary = { ...EMPTY_STATS, ...(summary || {}) };
  const expiredCount = Number(expirationSummary?.expiredCount || 0);
  const within30Count = Number(expirationSummary?.within30Count || 0);
  const cards = [
    { label: "전체 SW", value: safeSummary.total_software, tone: "blue" },
    { label: "영구", value: safeSummary.perpetual_count, tone: "green" },
    { label: "구독", value: safeSummary.subscription_count, tone: "amber" },
    { label: "사용중지", value: safeSummary.discontinued_count, tone: "red" },
  ];

  return (
    <section className="stats-summary software-stats" aria-labelledby="software-stats-title">
      <div className="section-heading">
        <div>
          <h2 id="software-stats-title">SW 요약</h2>
          <p>등록된 소프트웨어 기준입니다.</p>
        </div>
        {isLoading && <span className="inline-info">요약을 불러오는 중입니다.</span>}
        {error && !isLoading && <span className="inline-alert">요약을 불러오지 못했습니다.</span>}
      </div>

      <div className="stats-grid">
        {cards.map((card) => (
          <div className={`stats-card stats-card-${card.tone}`} key={card.label}>
            <div>
              <span>{card.label}</span>
              <strong>{Number(card.value || 0).toLocaleString("ko-KR")}개</strong>
            </div>
            <span className="stats-card-icon" aria-hidden="true">▦</span>
          </div>
        ))}
      </div>

      <div className={expiredCount || within30Count ? "software-expiration-alert warning" : "software-expiration-alert"}>
        {expiredCount || within30Count ? (
          <>
            <strong>만료 알림</strong>
            <span>만료된 SW {expiredCount.toLocaleString("ko-KR")}개</span>
            <span>30일 이내 만료 예정 SW {within30Count.toLocaleString("ko-KR")}개</span>
          </>
        ) : (
          <span>만료 위험 소프트웨어가 없습니다.</span>
        )}
      </div>
    </section>
  );
}

export default SoftwareStats;
