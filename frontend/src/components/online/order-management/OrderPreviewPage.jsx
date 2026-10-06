import React from "react";
import OrderEmptyTable from "./OrderEmptyTable.jsx";

function OrderPreviewPage() {
  return (
    <section className="online-order-panel">
      <div className="online-order-panel-heading"><h3>결과 미리보기</h3><span className="online-pending-label">준비 중</span></div>
      <p>가공된 주문의 상태와 상품 정보를 확인할 화면입니다.</p>
      <div className="online-order-toolbar-skeleton">
        <label>상태<select defaultValue="all" disabled><option value="all">전체</option><option>정상</option><option>매칭 필요</option><option>오류</option></select></label>
        <label>검색<input type="search" placeholder="주문번호 또는 상품명" disabled /></label>
      </div>
      <OrderEmptyTable
        columns={["주문번호", "주문일", "상품명", "옵션", "구분", "이카운트 상품코드", "수량", "매출액", "상태"]}
        emptyMessage="아직 가공된 데이터가 없습니다."
      />
    </section>
  );
}

export default OrderPreviewPage;
