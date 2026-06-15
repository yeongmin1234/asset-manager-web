import React from "react";

function DepartmentStats({ items, isLoading, error }) {
  const safeItems = Array.isArray(items) ? items : [];

  return (
    <section className="department-stats" aria-labelledby="department-stats-title">
      <div className="section-heading">
        <div>
          <h2 id="department-stats-title">부서별 통계</h2>
          <p>부서 기준 자산 수입니다.</p>
        </div>
        {isLoading && <span className="inline-info">부서 통계를 불러오는 중입니다.</span>}
        {error && !isLoading && (
          <span className="inline-alert">부서별 통계를 불러오지 못했습니다.</span>
        )}
      </div>

      {error && !isLoading && <p className="state-detail">{error}</p>}

      {!error && !isLoading && safeItems.length === 0 && (
        <div className="state-panel">표시할 부서별 자산 통계가 없습니다.</div>
      )}

      {!error && safeItems.length > 0 && (
        <div className="category-stats-grid">
          {safeItems.map((item) => (
            <div className="category-stat-card" key={item.department_name}>
              <span>{item.department_name || "부서 미지정"}</span>
              <strong>{Number(item.asset_count || 0).toLocaleString("ko-KR")}개</strong>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default DepartmentStats;
