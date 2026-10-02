import React from "react";
import "./online.css";

function OrderManagementPage() {
  return (
    <div className="online-page online-order-page">
      <div className="portal-screen-heading">
        <h2>발주 관리</h2>
        <p>온라인 TEAM 발주 관련 업무를 관리합니다.</p>
      </div>
      <section className="online-order-placeholder" aria-label="발주 관리 안내">
        <span className="online-pending-label">준비 중</span>
        <p>상세 기능은 추후 업무 협의 후 추가될 예정입니다.</p>
      </section>
    </div>
  );
}

export default OrderManagementPage;
