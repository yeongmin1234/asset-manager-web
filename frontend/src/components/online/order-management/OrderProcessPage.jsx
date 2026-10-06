import React, { useState } from "react";
import OrderSummaryCards from "./OrderSummaryCards.jsx";

const STEPS = ["스마트스토어 원본 Excel 업로드", "1차 가공", "상품/사은품 매칭", "2차 가공", "오류 검증", "결과 미리보기", "SCM 최종 Excel 생성"];

function OrderProcessPage({ currentUser }) {
  const [selectedFileName, setSelectedFileName] = useState("");
  return (
    <>
      <section className="online-order-panel" aria-label="발주 파일 가공 입력">
        <div className="online-order-panel-heading"><h3>발주 파일 가공</h3><span className="online-pending-label">준비 중</span></div>
        <p>스마트스토어 원본 Excel을 선택할 수 있습니다. 서버 업로드와 가공은 다음 단계에서 연결됩니다.</p>
        <div className="online-order-form-grid">
          <label>채널<select defaultValue="smartstore" disabled><option value="smartstore">스마트스토어</option></select></label>
          <label>담당자<input value={currentUser?.name || ""} readOnly /></label>
        </div>
        <div className="online-order-upload-area">
          <label htmlFor="online-order-file">스마트스토어 원본 Excel 선택</label>
          <input id="online-order-file" type="file" accept=".xlsx,.xls" onChange={(event) => setSelectedFileName(event.target.files?.[0]?.name || "")} />
          <span>.xlsx / .xls · 선택한 파일은 서버에 전송되지 않습니다.</span>
          <strong aria-live="polite">{selectedFileName || "선택된 파일 없음"}</strong>
        </div>
        <button type="button" className="primary-action" disabled>가공 시작</button>
        <p className="online-order-action-note">다음 단계에서 Excel 가공 기능이 연결됩니다.</p>
      </section>
      <section className="online-order-panel" aria-label="처리 흐름">
        <h3>처리 흐름</h3>
        <ol className="online-order-steps">{STEPS.map((step) => <li key={step}>{step}</li>)}</ol>
      </section>
      <section className="online-order-panel" aria-label="처리 결과 요약">
        <h3>처리 결과 요약</h3>
        <OrderSummaryCards items={[
          { label: "총 주문", value: 0 }, { label: "정상", value: 0 },
          { label: "매칭 필요", value: 0 }, { label: "오류", value: 0 },
        ]} />
      </section>
    </>
  );
}

export default OrderProcessPage;
