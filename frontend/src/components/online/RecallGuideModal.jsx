import React, { useState } from "react";

const GUIDE_STEPS = [
  ["리콜 대상 등록", "각 채널에서 전달받은 리콜 대상 Raw Data를 등록합니다."],
  ["리콜 신청 데이터 등록", "네이버 서베이 등으로 실제 신청한 고객 데이터를 등록합니다."],
  ["기존 데이터 매칭 실행", "기존 리콜 대상과 신청 데이터를 시리얼번호/연락처 기준으로 다시 매칭합니다."],
  ["중복 확인", "연락처 또는 시리얼번호 중복 건을 별도로 확인하고 처리합니다."],
  ["SCM 발주 대상", "신청 완료 후 발주 대상 고객을 확인하고 SCM 발주 Excel을 생성합니다."],
];

export default function RecallGuideModal({ onClose }) {
  const [dontShowAgain, setDontShowAgain] = useState(false);
  return <div className="online-upload-backdrop">
    <section className="online-upload-modal online-recall-guide-modal" role="dialog" aria-modal="true" aria-labelledby="online-recall-guide-title">
      <header className="online-upload-header"><h2 id="online-recall-guide-title">리콜 관리 사용 안내</h2></header>
      <div className="online-recall-guide-body">
        <ol className="online-recall-guide-steps">{GUIDE_STEPS.map(([title, description]) =>
          <li key={title}><strong>{title}</strong><p>{description}</p></li>)}</ol>
        <div className="online-recall-guide-flow"><strong>업무 흐름</strong><p>리콜 대상 등록 → 리콜 신청 데이터 등록 → 자동 매칭 → 중복/확인 필요 검토 → SCM 발주 대상 → 발주 Excel 생성</p></div>
      </div>
      <footer className="online-upload-footer online-recall-guide-footer">
        <label><input type="checkbox" checked={dontShowAgain} onChange={(event) => setDontShowAgain(event.target.checked)} /> 앞으로 보지 않음</label>
        <button type="button" className="primary-action" onClick={() => onClose(dontShowAgain)}>닫기</button>
      </footer>
    </section>
  </div>;
}
