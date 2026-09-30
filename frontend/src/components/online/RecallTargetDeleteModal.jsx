import React, { useState } from "react";
import { createPortal } from "react-dom";

export default function RecallTargetDeleteModal({ count, saving, error, onClose, onConfirm }) {
  const [reason, setReason] = useState("");
  return createPortal(<div className="online-upload-backdrop" onMouseDown={(event) => {
    if (event.target === event.currentTarget && !saving) onClose();
  }}>
    <form className="online-upload-modal online-recall-delete-modal" role="dialog" aria-modal="true" aria-labelledby="target-delete-title"
      onSubmit={(event) => { event.preventDefault(); if (!saving && reason.trim()) onConfirm(reason.trim()); }}>
      <header className="online-upload-header"><h2 id="target-delete-title">리콜 대상 선택 삭제</h2></header>
      <div className="online-recall-delete-body">
        <p>선택한 {count}건의 리콜 대상을 삭제하시겠습니까?<br />삭제된 대상은 리콜 대상 목록과 통계에서 제외됩니다. 연결된 신청 데이터와 이력은 유지됩니다.</p>
        <label>삭제 사유<textarea value={reason} required maxLength={255} disabled={saving} onChange={(event) => setReason(event.target.value)} placeholder="삭제 사유를 입력해주세요." /></label>
        {error && <p className="online-recall-bulk-error" role="alert">{error}</p>}
      </div>
      <footer className="online-upload-footer">
        <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>취소</button>
        <button type="submit" className="secondary-button online-recall-delete-button" disabled={saving || !reason.trim()}>{saving ? "삭제 중..." : "삭제"}</button>
      </footer>
    </form>
  </div>, document.body);
}
