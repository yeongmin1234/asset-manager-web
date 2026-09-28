import React from "react";

const FEATURES = [
  { title: "리콜 관리", description: "리콜 대상 고객, 접수, 주문, 발송 현황을 관리합니다.", sectionId: "online-recall" },
  { title: "주문 관리", description: "향후 온라인 주문 관련 기능 예정" },
  { title: "고객 관리", description: "향후 고객 관리 기능 예정" },
  { title: "배송 관리", description: "향후 배송 관련 기능 예정" },
];

function OnlineFeatureCards({ onNavigate }) {
  return (
    <section className="online-feature-grid" aria-label="온라인 업무 메뉴">
      {FEATURES.map(({ title, description, sectionId }) => (
        <article className="online-feature-card" key={title}>
          <div>
            <h3>{title}</h3>
            <p>{description}</p>
          </div>
          {sectionId ? (
            <button type="button" className="secondary-button" onClick={() => onNavigate?.(sectionId)}>
              바로가기
            </button>
          ) : (
            <span className="online-pending-label">준비 중</span>
          )}
        </article>
      ))}
    </section>
  );
}

export default OnlineFeatureCards;
