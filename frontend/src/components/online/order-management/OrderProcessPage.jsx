import React from "react";

const STEPS = ["스마트스토어 원본 Excel 업로드", "1차 가공", "상품/사은품 매칭", "2차 가공", "오류 검증", "결과 미리보기", "SCM 최종 Excel 생성"];

function OrderProcessPage({ currentUser }) {
  return (
    <>
      <section className="online-order-panel" aria-label="발주 파일 가공 입력">
        <div className="online-order-panel-heading"><h3>발주 파일 가공</h3><span className="online-pending-label">준비 중</span></div>
        <p>스마트스토어 파일을 처리할 화면입니다. 업로드와 가공은 아직 사용할 수 없습니다.</p>
        <div className="online-order-form-grid">
          <label>채널<select value="smartstore" disabled><option value="smartstore">스마트스토어</option></select></label>
          <label>담당자<input value={currentUser?.name || ""} readOnly /></label>
        </div>
        <div className="online-order-upload-area" aria-label="파일 업로드 준비 중">원본 Excel 업로드 영역 · 준비 중</div>
        <button type="button" className="primary-action" disabled>가공 시작</button>
      </section>
      <section className="online-order-panel" aria-label="처리 흐름">
        <h3>처리 흐름</h3>
        <ol className="online-order-steps">{STEPS.map((step) => <li key={step}>{step}</li>)}</ol>
      </section>
      <section className="online-order-panel" aria-label="처리 결과 요약">
        <h3>처리 결과 요약</h3><p>가공 결과가 준비되면 건수와 오류 현황이 표시됩니다.</p>
      </section>
    </>
  );
}

export default OrderProcessPage;
