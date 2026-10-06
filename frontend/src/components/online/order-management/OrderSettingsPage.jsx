import React from "react";

function OrderSettingsPage() {
  return (
    <>
      <section className="online-order-panel"><div className="online-order-panel-heading"><h3>채널 설정</h3><span className="online-pending-label">준비 중</span></div><label className="online-order-setting-row"><span>스마트스토어 사용 여부</span><input type="checkbox" checked readOnly disabled /></label></section>
      <section className="online-order-panel"><h3>파일 설정</h3><div className="online-order-setting-row"><span>허용 파일 형식</span><strong>.xlsx / .xls</strong></div><div className="online-order-setting-row"><span>최대 파일 크기</span><strong>추후 확정</strong></div></section>
      <section className="online-order-panel"><h3>가공 설정</h3><p className="online-order-empty">자동 가공 기능 준비 중</p></section>
    </>
  );
}

export default OrderSettingsPage;
