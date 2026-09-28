import React, { useState } from "react";
import RecallFilters from "./RecallFilters.jsx";
import RecallSummaryCards from "./RecallSummaryCards.jsx";
import RecallTable from "./RecallTable.jsx";
import RecallUploadModal from "./RecallUploadModal.jsx";
import "./online.css";

function RecallManagementPage() {
  const [uploadMode, setUploadMode] = useState(null);

  return (
    <div className="online-page">
      <div className="portal-screen-heading online-recall-heading">
        <div>
          <h2>리콜 관리</h2>
          <p>리콜 대상 고객의 접수, 주문, 발송 진행 상태를 관리합니다.</p>
        </div>
        <div className="online-recall-actions">
          <button type="button" className="secondary-button" onClick={() => setUploadMode("application")}>접수 데이터 등록</button>
          <button type="button" className="primary-action" onClick={() => setUploadMode("target")}>리콜 대상 등록</button>
        </div>
      </div>
      <RecallSummaryCards />
      <section className="online-recall-list" aria-label="리콜 대상 목록">
        <RecallFilters />
        <RecallTable />
      </section>
      {uploadMode && <RecallUploadModal mode={uploadMode} onClose={() => setUploadMode(null)} />}
    </div>
  );
}

export default RecallManagementPage;
