import React from "react";

function MonthlyStats({ items, isLoading, error }) {
  const safeItems = Array.isArray(items) ? items : [];
  const maxValue = Math.max(
    1,
    ...safeItems.map((item) =>
      Math.max(Number(item.registered_count || 0), Number(item.disposed_count || 0)),
    ),
  );

  return (
    <section className="monthly-stats" aria-labelledby="monthly-stats-title">
      <div className="section-heading">
        <div>
          <h2 id="monthly-stats-title">최근 3개월 추이</h2>
          <p>등록과 폐기 흐름입니다.</p>
        </div>
        {isLoading && <span className="inline-info">월별 통계를 불러오는 중입니다.</span>}
        {error && !isLoading && (
          <span className="inline-alert">월별 통계를 불러오지 못했습니다.</span>
        )}
      </div>

      {error && !isLoading && <p className="state-detail">{error}</p>}

      {!error && !isLoading && safeItems.length === 0 && (
        <div className="state-panel">표시할 월별 통계가 없습니다.</div>
      )}

      {!error && safeItems.length > 0 && (
        <div className="monthly-stats-list">
          {safeItems.map((item) => {
            const registeredCount = Number(item.registered_count || 0);
            const disposedCount = Number(item.disposed_count || 0);
            return (
              <div className="monthly-stat-row" key={item.month}>
                <strong>{item.month}</strong>
                <div className="monthly-bars">
                  <MetricBar
                    label="등록"
                    value={registeredCount}
                    maxValue={maxValue}
                    tone="registered"
                  />
                  <MetricBar
                    label="폐기"
                    value={disposedCount}
                    maxValue={maxValue}
                    tone="disposed"
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function MetricBar({ label, value, maxValue, tone }) {
  const width = value > 0 ? `${Math.max(4, Math.round((value / maxValue) * 100))}%` : "0%";

  return (
    <div className="monthly-bar-line">
      <span>{label}</span>
      <div className="monthly-bar-track" aria-hidden="true">
        <div className={`monthly-bar-fill monthly-bar-${tone}`} style={{ width }} />
      </div>
      <strong>{value.toLocaleString("ko-KR")}개</strong>
    </div>
  );
}

export default MonthlyStats;
