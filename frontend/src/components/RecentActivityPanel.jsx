import React from "react";

function RecentActivityPanel({ assets = [], onNavigate }) {
  const recentAssets = Array.isArray(assets) ? assets.slice(0, 4) : [];

  return (
    <section className="portal-side-card" id="activity" aria-labelledby="recent-activity-title">
      <div className="side-card-heading">
        <h3 id="recent-activity-title">최근 변경 이력</h3>
        <button type="button" className="link-button" onClick={() => onNavigate?.("assets")}>
          더보기
        </button>
      </div>

      {recentAssets.length === 0 ? (
        <div className="recent-empty">
          <strong>최근 활동이 없습니다.</strong>
          <span>자산 변경 후 표시됩니다.</span>
        </div>
      ) : (
        <div className="recent-activity-list">
          {recentAssets.map((asset) => (
            <div className="recent-activity-item" key={asset.id}>
              <span className="activity-dot" />
              <div>
                <strong>{asset.name}</strong>
                <p>
                  {asset.department_name || asset.user_name || "부서 미지정"} · {asset.status || "-"}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default RecentActivityPanel;
