import React from "react";

function PortalHero({ onNavigate }) {
  return (
    <section className="portal-hero" aria-labelledby="portal-hero-title">
      <div className="portal-hero-copy">
        <p className="eyebrow">Asset Portal</p>
        <h2 id="portal-hero-title">안녕하세요, 관리자님!</h2>
        <p>사내 자산을 한눈에 관리하고 효율적으로 운영하세요.</p>
        <div className="portal-hero-actions">
          <button type="button" className="primary-action" onClick={() => onNavigate?.("quick")}>
            빠른 등록
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("assets")}>
            자산 목록
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("excel")}>
            엑셀 관리
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("reports")}>
            통계 보기
          </button>
        </div>
      </div>
      <div className="portal-hero-visual" aria-hidden="true">
        <div className="hero-screen">
          <span />
          <span />
          <span />
          <strong />
        </div>
      </div>
    </section>
  );
}

export default PortalHero;
