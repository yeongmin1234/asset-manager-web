import React from "react";
import OrderEmptyTable from "./OrderEmptyTable.jsx";

function OrderHistoryPage() {
  return (
    <section className="online-order-panel">
      <div className="online-order-panel-heading"><h3>가공 이력</h3><span className="online-pending-label">준비 중</span></div>
      <p>파일별 가공 결과와 다운로드 내역을 확인할 화면입니다.</p>
      <OrderEmptyTable
        columns={["가공일시", "채널", "담당자", "원본 파일명", "주문 건수", "정상", "매칭 필요", "오류", "상태", "다운로드"]}
        emptyMessage="아직 가공 이력이 없습니다."
      />
    </section>
  );
}

export default OrderHistoryPage;
