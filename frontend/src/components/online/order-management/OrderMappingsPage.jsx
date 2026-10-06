import React from "react";
import OrderEmptyTable from "./OrderEmptyTable.jsx";

function OrderMappingsPage() {
  return (
    <section className="online-order-panel">
      <div className="online-order-panel-heading"><h3>상품 매칭 관리</h3><span className="online-pending-label">준비 중</span></div>
      <p>채널 상품과 이카운트 상품의 매핑을 관리할 화면입니다.</p>
      <div className="online-order-toolbar-skeleton">
        <label>검색<input type="search" placeholder="채널 상품코드 또는 상품명" disabled /></label>
        <label>채널<select defaultValue="smartstore" disabled><option value="smartstore">스마트스토어</option></select></label>
        <label>구분<select defaultValue="all" disabled><option value="all">전체</option><option>본품</option><option>사은품</option></select></label>
        <button type="button" className="secondary-button" disabled>매핑 추가</button>
      </div>
      <OrderEmptyTable
        columns={["채널", "채널 상품코드", "옵션", "이카운트 상품코드", "이카운트 상품명", "구분", "수량", "사용 여부"]}
        emptyMessage="등록된 상품 매핑이 없습니다."
      />
    </section>
  );
}

export default OrderMappingsPage;
