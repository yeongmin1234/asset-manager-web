import React from "react";

function CategoryStats({ items, isLoading, error }) {
  const safeItems = Array.isArray(items) ? items : [];

  return (
    <section className="category-stats" aria-labelledby="category-stats-title">
      <div className="section-heading">
        <div>
          <h2 id="category-stats-title">분류별 통계</h2>
          <p>분류 기준 자산 수입니다.</p>
        </div>
        {isLoading && <span className="inline-info">분류 통계를 불러오는 중입니다.</span>}
        {error && !isLoading && (
          <span className="inline-alert">분류별 통계를 불러오지 못했습니다.</span>
        )}
      </div>

      {error && !isLoading && <p className="state-detail">{error}</p>}

      {!error && !isLoading && safeItems.length === 0 && (
        <div className="state-panel">표시할 분류별 자산 통계가 없습니다.</div>
      )}

      {!error && safeItems.length > 0 && (
        <div className="category-stats-grid">
          {safeItems.map((item) => (
            <div className="category-stat-card" key={item.category_name}>
              <span>{item.category_name || "미분류"}</span>
              <strong>{Number(item.asset_count || 0).toLocaleString("ko-KR")}개</strong>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default CategoryStats;
