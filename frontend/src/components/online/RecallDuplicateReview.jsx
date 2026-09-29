import React, { useState } from "react";
import { createPortal } from "react-dom";
import { resolveRecallDuplicate } from "../../api/client.js";
import { formatPhoneForDisplay, formatRecallDate } from "./onlineDisplayUtils.js";

const REASONS = { PHONE: "연락처", SERIAL: "시리얼번호", PHONE_AND_SERIAL: "연락처·시리얼번호" };

function RecallDuplicateReview({ items, isLoading, error, onDetail, onResolved }) {
  const [decision, setDecision] = useState(null);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");

  const openDecision = (item, action) => {
    setDecision({ id: item.id, action });
    setReason("");
    setActionError("");
  };
  const saveDecision = async (event) => {
    event.preventDefault();
    if (!reason.trim() || saving) return;
    setSaving(true);
    setActionError("");
    try {
      await resolveRecallDuplicate(decision.id, decision.action, reason.trim());
      setDecision(null);
      onResolved();
    } catch (caught) {
      setActionError(caught?.message || "중복 확인 처리에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return <>
    <div className="online-recall-table-wrap">
      <table className="online-recall-table online-duplicate-table">
        <thead><tr>{["고객명", "연락처", "시리얼번호", "중복 사유", "기존 접수 정보", "신규 접수 정보", "상세", "처리"].map((label) => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{isLoading ? <tr><td colSpan={8} className="online-recall-empty">중복 확인 건을 불러오는 중입니다.</td></tr> : error ? <tr><td colSpan={8} className="online-recall-empty">{error}</td></tr> : items.length ? items.map((item) => {
          const reference = item.duplicate_reference;
          return <tr key={item.id}>
            <td>{item.customer_name}</td>
            <td>{formatPhoneForDisplay(item.phone_original)}</td>
            <td>{item.serial_number || "-"}</td>
            <td><span className="online-preview-badge online-preview-badge-duplicate">{REASONS[item.duplicate_reason] || item.duplicate_reason}</span></td>
            <td className="online-duplicate-info">{reference ? <><strong>#{reference.id} · {reference.customer_name}</strong><span>{formatRecallDate(reference.application_date)} · {formatPhoneForDisplay(reference.phone_original)} · {reference.serial_number || "시리얼 없음"}</span></> : <span>참조 접수 정보 없음</span>}</td>
            <td className="online-duplicate-info"><strong>#{item.id} · {item.customer_name}</strong><span>{formatRecallDate(item.application_date)} · {formatPhoneForDisplay(item.phone_original)} · {item.serial_number || "시리얼 없음"}</span></td>
            <td><button type="button" className="secondary-button" onClick={() => onDetail(item.id)}>상세</button></td>
            <td className="online-duplicate-actions"><button type="button" className="secondary-button" onClick={() => openDecision(item, "NORMAL")}>정상 건으로 처리</button><button type="button" className="secondary-button" onClick={() => openDecision(item, "KEEP")}>중복 건 유지</button></td>
          </tr>;
        }) : <tr><td colSpan={8} className="online-recall-empty">중복 확인 건이 없습니다.</td></tr>}</tbody>
      </table>
    </div>
    {decision && createPortal(<div className="online-upload-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setDecision(null); }}>
      <form className="online-upload-modal online-duplicate-decision-modal" role="dialog" aria-modal="true" onSubmit={saveDecision}>
        <header className="online-upload-header"><h2>{decision.action === "NORMAL" ? "정상 건으로 처리" : "중복 건 유지"}</h2></header>
        <label className="online-duplicate-reason">처리 사유<select value={reason} required autoFocus onChange={(event) => setReason(event.target.value)}><option value="">사유 선택</option>{(decision.action === "NORMAL" ? ["별도 접수 확인", "잘못된 중복 판정"] : ["실제 중복 확인", "추가 검토 필요"]).map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
        {actionError && <p className="online-recall-bulk-error" role="alert">{actionError}</p>}
        <footer className="online-upload-footer"><button type="button" className="secondary-button" disabled={saving} onClick={() => setDecision(null)}>취소</button><button type="submit" className="primary-action" disabled={saving || !reason.trim()}>{saving ? "처리 중..." : "처리"}</button></footer>
      </form>
    </div>, document.body)}
  </>;
}

export default RecallDuplicateReview;
