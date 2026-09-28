import React from "react";
import RecallFilters from "./RecallFilters.jsx";
import RecallSummaryCards from "./RecallSummaryCards.jsx";
import RecallTable from "./RecallTable.jsx";
import "./online.css";

function RecallManagementPage() {
  return (
    <div className="online-page">
      <div className="portal-screen-heading online-recall-heading">
        <div>
          <h2>리콜 관리</h2>
          <p>리콜 대상 고객의 접수, 주문, 발송 진행 상태를 관리합니다.</p>
        </div>
        <div className="online-recall-actions" aria-label="추후 제공 예정인 작업">
          <button type="button" className="secondary-button" disabled title="준비 중">접수 데이터 등록</button>
          <button type="button" className="primary-action" disabled title="준비 중">리콜 대상 등록</button>
        </div>
      </div>
      <RecallSummaryCards />
      <section className="online-recall-list" aria-label="리콜 대상 목록">
        <RecallFilters />
        <RecallTable />
      </section>
    </div>
  );
}

export default RecallManagementPage;
