import React, { useEffect, useState } from "react";
import { getOrderChannels } from "../../../api/client.js";
import OrderSummaryCards from "./OrderSummaryCards.jsx";

const STEPS = ["원본 Excel 업로드", "1차 가공", "상품/사은품 매칭", "2차 가공", "오류 검증", "결과 미리보기", "SCM 최종 Excel 생성"];

function OrderProcessPage({ currentUser }) {
  const [selectedFileName, setSelectedFileName] = useState("");
  const [channels, setChannels] = useState([]);
  const [selectedCode, setSelectedCode] = useState("");
  const [channelError, setChannelError] = useState("");
  const selectedChannel = channels.find((channel) => channel.code === selectedCode);

  useEffect(() => {
    let alive = true;
    getOrderChannels(true)
      .then((items) => {
        if (!alive) return;
        setChannels(items);
        setSelectedCode((previous) => items.some((item) => item.code === previous)
          ? previous : (items.find((item) => item.is_default) || items[0])?.code || "");
      })
      .catch((failure) => { if (alive) setChannelError(failure.message); });
    return () => { alive = false; };
  }, []);

  return (
    <>
      <section className="online-order-panel" aria-label="발주 파일 가공 입력">
        <div className="online-order-panel-heading"><h3>발주 파일 가공</h3><span className="online-pending-label">준비 중</span></div>
        <p>사용 중인 판매 채널과 원본 Excel을 선택할 수 있습니다. 서버 업로드와 가공은 다음 단계에서 연결됩니다.</p>
        <div className="online-order-form-grid">
          <label>채널<select value={selectedCode} onChange={(event) => setSelectedCode(event.target.value)} disabled={channels.length === 0}>
            {channels.length === 0 && <option value="">사용 중인 채널 없음</option>}
            {channels.map((channel) => <option key={channel.id} value={channel.code}>{channel.name}</option>)}
          </select></label>
          <label>담당자<input value={currentUser?.name || ""} readOnly /></label>
        </div>
        {channelError && <p className="online-order-channel-error" role="alert">{channelError}</p>}
        {selectedChannel && !selectedChannel.processing_supported && <p className="online-order-channel-notice" role="status">현재 자동 가공을 지원하지 않는 채널입니다.</p>}
        <div className="online-order-upload-area">
          <label htmlFor="online-order-file">{selectedChannel?.name || "판매 채널"} 원본 Excel 선택</label>
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
