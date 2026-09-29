import React, { useEffect, useState } from "react";
import { getRecallApplication, updateRecallApplicationStatus } from "../../api/client.js";
import {
  displayRecallStatus,
  formatPhoneForDisplay,
  formatRecallDate,
  formatRecallDateTime,
  recallStatusClass,
  recallManualTargets,
} from "./onlineDisplayUtils.js";

const show = (value) => value === null || value === undefined || value === "" ? "-" : value;

function Field({ label, children, wide = false }) {
  return <div className={`online-detail-field${wide ? " online-detail-field-wide" : ""}`}><dt>{label}</dt><dd>{children}</dd></div>;
}

export function RecallRecoveryAction({ reason, onReasonChange, onSubmit, saving }) {
  return (
    <form className="online-detail-recovery-form" onSubmit={onSubmit}>
      <label htmlFor="online-recall-recovery-reason">복구 사유</label>
      <input id="online-recall-recovery-reason" list="online-recall-recovery-reasons" value={reason} onChange={(event) => onReasonChange(event.target.value)} maxLength={255} placeholder="사유를 선택하거나 직접 입력" required disabled={saving} />
      <datalist id="online-recall-recovery-reasons">
        <option value="오처리" />
        <option value="잘못된 상태 변경" />
        <option value="발송 취소" />
        <option value="기타" />
      </datalist>
      <button type="submit" className="secondary-button" disabled={saving || !reason.trim()}>{saving ? "복구 중..." : "접수완료로 되돌리기"}</button>
    </form>
  );
}

export function RecallDetailStatusActions({ detail, status, onStatusChange, reason, onReasonChange, recoveryReason, onRecoveryReasonChange, onSubmit, onRecover, saving }) {
  if (detail.current_status === "SHIPPED") {
    return <RecallRecoveryAction reason={recoveryReason} onReasonChange={onRecoveryReasonChange} onSubmit={onRecover} saving={saving} />;
  }
  const manualTargets = recallManualTargets(detail.current_status);
  return (
    <form className="online-detail-status-form" onSubmit={onSubmit}>
      <label>변경 상태<select value={status} onChange={(event) => onStatusChange(event.target.value)} disabled={saving || manualTargets.length === 0}>
        <option value={detail.current_status} disabled>{displayRecallStatus(detail.current_status)} (현재)</option>
        {manualTargets.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select></label>
      <label>변경 사유<input value={reason} onChange={(event) => onReasonChange(event.target.value)} maxLength={255} placeholder="변경 사유를 입력해주세요" disabled={saving || manualTargets.length === 0} /></label>
      <button type="submit" className="primary-action" disabled={saving || !reason.trim() || !manualTargets.some((option) => option.value === status)}>{saving ? "저장 중..." : "상태 변경"}</button>
    </form>
  );
}

function RecallDetailModal({ applicationId, onClose, onChanged }) {
  const [detail, setDetail] = useState(null);
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [recoveryReason, setRecoveryReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    getRecallApplication(applicationId).then((result) => {
      if (!active) return;
      setDetail(result);
      setStatus(result.current_status);
    }).catch((caught) => {
      if (active) setError(caught?.message || "상세 정보를 불러오지 못했습니다.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [applicationId]);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape" && !saving) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, saving]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!reason.trim()) {
      setError("상태 변경 사유를 입력해주세요.");
      return;
    }
    setSaving(true);
    try {
      const result = await updateRecallApplicationStatus(applicationId, status, reason.trim());
      setDetail(result.application);
      setStatus(result.application.current_status);
      setReason("");
      setMessage(result.changed ? "상태가 변경되었습니다." : "현재 상태와 같아 변경하지 않았습니다.");
      if (result.changed) onChanged();
    } catch (caught) {
      setError(caught?.message || "상태를 변경하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const handleRecover = async (event) => {
    event.preventDefault();
    const cleanedReason = recoveryReason.trim();
    if (detail?.current_status !== "SHIPPED" || saving) return;
    if (!cleanedReason) {
      setError("복구 사유를 입력해주세요.");
      return;
    }
    if (!window.confirm("발송완료 상태를 접수완료로 되돌리시겠습니까?")) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await updateRecallApplicationStatus(applicationId, "APPLICATION_RECEIVED", cleanedReason);
      setDetail(result.application);
      setStatus(result.application.current_status);
      setRecoveryReason("");
      setMessage(result.changed ? "접수완료 상태로 되돌렸습니다." : "이미 접수완료 상태입니다.");
      if (result.changed) onChanged();
    } catch (caught) {
      setError(caught?.message || "발송완료 상태를 되돌리지 못했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="online-upload-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
      <section className="online-detail-modal" role="dialog" aria-modal="true" aria-labelledby="online-detail-title">
        <header className="online-upload-header">
          <div><h2 id="online-detail-title">리콜 고객 상세</h2><p>접수 정보와 상태 이력을 확인합니다.</p></div>
          <button type="button" className="secondary-button" onClick={onClose} disabled={saving}>닫기</button>
        </header>
        <div className="online-detail-body">
          {loading && <p className="online-detail-message">상세 정보를 불러오는 중입니다.</p>}
          {!loading && !detail && <p className="online-detail-error" role="alert">{error}</p>}
          {detail && <>
            <section className="online-detail-section">
              <h3>고객 정보</h3>
              <dl className="online-detail-grid">
                <Field label="고객명">{show(detail.customer_name)}</Field>
                <Field label="연락처"><span title={detail.phone_normalized ? `비교용: ${detail.phone_normalized}` : undefined}>{show(formatPhoneForDisplay(detail.phone_original))}</span></Field>
                <Field label="주소" wide>{show(detail.address)}</Field>
              </dl>
            </section>
            <section className="online-detail-section">
              <h3>신청 정보</h3>
              <dl className="online-detail-grid">
                <Field label="신청일자">{formatRecallDate(detail.application_date)}</Field>
                <Field label="수량">{show(detail.quantity)}</Field>
                <Field label="시리얼번호">{show(detail.serial_number)}</Field>
                <Field label="LOT 번호">{show(detail.lot_number)}</Field>
                <Field label="기존 필터 회수 동의">{show(detail.pickup_agreement)}</Field>
                <Field label="회수 일자">{formatRecallDate(detail.pickup_date)}</Field>
                <Field label="대체 필터 출고 동의">{show(detail.replacement_shipping_agreement)}</Field>
                <Field label="원본 업로드 파일">{show(detail.upload_batch?.source_filename)}{detail.upload_batch?.id ? ` · Batch #${detail.upload_batch.id}` : ""}</Field>
                <Field label="메모" wide>{show(detail.memo)}</Field>
              </dl>
            </section>
            <section className="online-detail-section">
              <h3>상태 정보</h3>
              <dl className="online-detail-grid">
                <Field label="현재 상태"><span className={`online-recall-status ${recallStatusClass(detail.current_status)}`}>{displayRecallStatus(detail.current_status)}</span></Field>
                <Field label="등록일시">{formatRecallDateTime(detail.created_at)}</Field>
                <Field label="등록자">{show(detail.created_by_name || (detail.created_by ? `사용자 #${detail.created_by}` : ""))}</Field>
              </dl>
              <RecallDetailStatusActions detail={detail} status={status} onStatusChange={setStatus} reason={reason} onReasonChange={setReason} recoveryReason={recoveryReason} onRecoveryReasonChange={setRecoveryReason} onSubmit={handleSubmit} onRecover={handleRecover} saving={saving} />
              {error && <p className="online-detail-error" role="alert">{error}</p>}
              {message && <p className="online-detail-success" role="status">{message}</p>}
            </section>
            <section className="online-detail-section">
              <h3>상태 이력</h3>
              {(detail.status_history || []).length === 0 ? <p className="online-detail-message">상태 이력이 없습니다.</p> :
                <div className="online-detail-history">
                  {detail.status_history.map((entry) => <div className="online-detail-history-item" key={entry.id}>
                    <strong>{formatRecallDateTime(entry.changed_at)}</strong>
                    <span>{entry.previous_status ? displayRecallStatus(entry.previous_status) : "최초 등록"} → {displayRecallStatus(entry.new_status)}</span>
                    <span>{entry.change_type === "MANUAL" ? "수동 변경" : entry.change_type === "EXCEL_REGISTRATION" ? "Excel 접수 등록" : show(entry.change_type)}</span>
                    <span>사유: {show(entry.reason)}</span>
                    <span>변경자: {show(entry.changed_by_name || (entry.changed_by ? `사용자 #${entry.changed_by}` : ""))}</span>
                  </div>)}
                </div>}
            </section>
            {(detail.duplicate_flag || detail.duplicate_history?.length > 0) && <section className="online-detail-section">
              <h3>중복 확인</h3>
              <dl className="online-detail-grid">
                <Field label="확인 상태">{detail.duplicate_flag ? "중복 확인 필요" : "정상 건으로 처리"}</Field>
                <Field label="중복 사유">{{ PHONE: "연락처", SERIAL: "시리얼번호", PHONE_AND_SERIAL: "연락처·시리얼번호" }[detail.duplicate_reason] || "-"}</Field>
                <Field label="참조 접수">{detail.duplicate_reference_id ? `#${detail.duplicate_reference_id}` : "-"}</Field>
              </dl>
              {(detail.duplicate_history || []).map((entry, index) => <div className="online-detail-history-item" key={index}>
                <strong>{formatRecallDateTime(entry.changed_at)}</strong>
                <span>{entry.action === "NORMAL" ? "정상 건으로 처리" : "중복 건 유지"}</span>
                <span>사유: {entry.reason}</span>
                <span>처리자: {entry.changed_by_name || `사용자 #${entry.changed_by}`}</span>
              </div>)}
            </section>}
          </>}
        </div>
      </section>
    </div>
  );
}

export default RecallDetailModal;
