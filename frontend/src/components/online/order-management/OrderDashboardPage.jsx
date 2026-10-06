import React from "react";
import OrderSummaryCards from "./OrderSummaryCards.jsx";

function OrderDashboardPage() {
  return (
    <>
      <section className="online-order-panel">
        <div className="online-order-panel-heading"><h3>발주 대시보드</h3><span className="online-pending-label">준비 중</span></div>
        <p>가공 현황은 기능 연결 후 표시됩니다. 아래 수치는 예시 빈 상태입니다.</p>
        <OrderSummaryCards items={[
          { label: "오늘 가공", value: 0 }, { label: "정상", value: 0 },
          { label: "매칭 필요", value: 0 }, { label: "오류", value: 0 },
        ]} />
      </section>
      <div className="online-order-two-columns">
        <section className="online-order-panel"><h3>최근 가공 이력</h3><p className="online-order-empty">아직 가공 이력이 없습니다.</p></section>
        <section className="online-order-panel"><h3>채널별 현황</h3><p className="online-order-empty">아직 채널별 처리 내역이 없습니다.</p></section>
      </div>
    </>
  );
}

export default OrderDashboardPage;
