import React, { useState } from "react";
import { createPortal } from "react-dom";

const DELETE_REASONS = ["잘못 등록", "테스트 데이터", "고객 요청", "중복 등록", "담당자 입력 오류", "기타"];

function RecallDeleteModal({ count, progressedCount = 0, saving, error, onClose, onConfirm }) {
  const [reasonCategory, setReasonCategory] = useState("");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const submit = (event) => {
    event.preventDefault();
    if (reasonCategory && reason.trim() && (!progressedCount || confirmed) && !saving) onConfirm(reasonCategory, reason.trim());
  };

  return createPortal(<div className="online-upload-backdrop" onMouseDown={(event) => {
    if (event.target === event.currentTarget && !saving) onClose();
  }}>
    <form className="online-upload-modal online-recall-delete-modal" role="dialog" aria-modal="true" aria-labelledby="online-recall-delete-title" onSubmit={submit}>
      <header className="online-upload-header"><h2 id="online-recall-delete-title">선택 삭제</h2></header>
      <div className="online-recall-delete-body">
        {progressedCount ? <p className="online-recall-delete-warning">선택한 {count}건 중 발주/발송 처리된 데이터 {progressedCount}건이 포함되어 있습니다.<br />삭제 시 현재 업무 목록에서는 제외되지만 기존 발주/발송/상태 이력은 보존됩니다.<br />정말 삭제하시겠습니까?</p> :
          <p>선택한 {count}건을 삭제하시겠습니까?<br />삭제된 건은 리콜 업무 목록에서 제외됩니다.</p>}
        <label>사유 분류<select value={reasonCategory} required disabled={saving} onChange={(event) => setReasonCategory(event.target.value)}>
          <option value="">선택해주세요</option>
          {DELETE_REASONS.map((option) => <option key={option} value={option}>{option}</option>)}
        </select></label>
        <label>삭제 사유<textarea value={reason} required maxLength={255} disabled={saving} onChange={(event) => setReason(event.target.value)} placeholder="삭제 사유를 입력해주세요." /></label>
        {progressedCount > 0 && <label className="online-recall-delete-confirm"><input type="checkbox" checked={confirmed} disabled={saving} onChange={(event) => setConfirmed(event.target.checked)} /> 발주/발송 이력이 보존됨을 확인했습니다.</label>}
        {error && <p className="online-recall-bulk-error" role="alert">{error}</p>}
      </div>
      <footer className="online-upload-footer">
        <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>취소</button>
        <button type="submit" className="secondary-button online-recall-delete-button" disabled={saving || !reasonCategory || !reason.trim() || (progressedCount > 0 && !confirmed)}>{saving ? "삭제 중..." : "최종 삭제"}</button>
      </footer>
    </form>
  </div>, document.body);
}

export default RecallDeleteModal;
