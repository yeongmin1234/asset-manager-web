import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { createRecallApplicationManually } from "../../api/client.js";

const FIELDS = [
  ["application_date", "신청일자", "date"], ["quantity", "수량", "number"],
  ["customer_name", "고객명", "text", true], ["phone_original", "연락처", "tel", true],
  ["address", "주소지", "text", true], ["memo", "메모", "text"],
  ["serial_number", "시리얼번호", "text"], ["lot_number", "LOT 번호", "text"],
  ["pickup_agreement", "기존 필터 회수 동의", "text"], ["pickup_date", "회수 일자", "date"],
  ["replacement_shipping_agreement", "대체 필터 출고 동의", "text"],
];
const INITIAL_VALUES = Object.fromEntries(FIELDS.map(([key]) => [key, ""]));

function RecallManualCreateModal({ onClose, onRegistered }) {
  const [values, setValues] = useState(INITIAL_VALUES);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const firstInput = useRef(null);

  useEffect(() => { firstInput.current?.focus(); }, []);
  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape" && !saving) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [saving, onClose]);

  const submit = async (event) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      await createRecallApplicationManually(values);
      onRegistered();
      onClose();
    } catch (caught) {
      const fields = caught?.detail?.detail?.fields;
      setError(fields ? Object.entries(fields).map(([field, message]) => `${FIELDS.find(([key]) => key === field)?.[1] || field}: ${message}`).join(" · ") :
        caught?.message || "리콜 신청을 등록하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return createPortal(<div className="online-upload-backdrop" onMouseDown={(event) => {
    if (event.target === event.currentTarget && !saving) onClose();
  }}>
    <form className="online-upload-modal online-recall-manual-modal" role="dialog" aria-modal="true" aria-labelledby="recall-manual-title" onSubmit={submit}>
      <header className="online-upload-header"><h2 id="recall-manual-title">리콜 신청 직접 등록</h2></header>
      <div className="online-recall-manual-grid">
        {FIELDS.map(([key, label, type, required], index) => <label key={key}>
          {label}{required && <span aria-hidden="true"> *</span>}
          <input ref={index === 0 ? firstInput : undefined} type={type} min={type === "number" ? "1" : undefined}
            value={values[key]} required={Boolean(required)} disabled={saving}
            onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} />
        </label>)}
      </div>
      {error && <p className="online-recall-manual-error" role="alert">{error}</p>}
      <footer className="online-upload-footer">
        <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>취소</button>
        <button type="submit" className="primary-action" disabled={saving}>{saving ? "저장 중..." : "저장"}</button>
      </footer>
    </form>
  </div>, document.body);
}

export default RecallManualCreateModal;
