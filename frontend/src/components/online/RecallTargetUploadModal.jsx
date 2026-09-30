import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { commitRecallTargetExcel, previewRecallTargetExcel } from "../../api/client.js";
import { formatPhoneForDisplay } from "./onlineDisplayUtils.js";

const COLUMNS = [
  ["sales_channel", "판매채널"], ["original_order_no", "주문번호"], ["customer_name", "고객명"],
  ["phone_raw", "연락처"], ["address", "주소"], ["delivery_message", "배송메시지"],
  ["serial_number", "시리얼번호"], ["lot_number", "LOT 번호"], ["purchase_date", "구매일"],
];
const STATUS = { valid: "정상", duplicate: "중복", review: "확인 필요", excluded: "제외" };

function RecallTargetUploadModal({ onClose, onRegistered }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef(null);
  useEffect(() => { fileInput.current?.focus(); }, []);
  useEffect(() => {
    const close = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [busy, onClose]);

  const analyze = async (event) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true); setError(""); setPreview(null);
    try { setPreview(await previewRecallTargetExcel(file)); }
    catch (caught) { setError(caught?.message || "리콜 대상 Excel을 분석하지 못했습니다."); }
    finally { setBusy(false); }
  };
  const commit = async () => {
    if (!preview || busy) return;
    setBusy(true); setError("");
    try {
      const registered = await commitRecallTargetExcel(file);
      setResult(registered);
      onRegistered?.(registered);
    } catch (caught) { setError(caught?.message || "리콜 대상을 등록하지 못했습니다."); }
    finally { setBusy(false); }
  };
  return createPortal(
    <div className="online-upload-backdrop" onMouseDown={() => { if (!busy) onClose(); }}>
      <section className="online-upload-modal online-target-modal" role="dialog" aria-modal="true" aria-labelledby="target-upload-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="online-upload-header"><div><h2 id="target-upload-title">리콜 대상 등록</h2><p>온라인 채널의 대상 Raw Data를 누적 등록합니다.</p></div><button type="button" className="secondary-button" onClick={onClose} disabled={busy}>닫기</button></header>
        {!result && <form className="online-upload-form" onSubmit={analyze}>
          <label htmlFor="target-excel-file">리콜 대상 Excel (.xlsx, 최대 5MB)</label>
          <div className="online-upload-controls"><input id="target-excel-file" ref={fileInput} type="file" accept=".xlsx" disabled={busy} onChange={(event) => {
            const chosen = event.target.files?.[0] || null;
            setPreview(null); setError(""); setFile(null);
            if (chosen && (!/\.xlsx$/i.test(chosen.name) || chosen.size > 5 * 1024 * 1024)) setError("5MB 이하 .xlsx 파일을 선택해주세요.");
            else setFile(chosen);
          }} /><button type="submit" className="primary-action" disabled={!file || busy}>{busy ? "처리 중..." : "미리보기"}</button></div>
        </form>}
        {error && <p className="online-upload-error" role="alert">{error}</p>}
        {preview && !result && <div className="online-preview-result">
          <p className="online-preview-sheet">시트: {preview.sheet_name}</p>
          <div className="online-preview-summary" aria-label="리콜 대상 미리보기 요약">{[["total_rows", "전체"], ["valid", "정상"], ["duplicate", "중복"], ["review", "확인 필요"], ["excluded", "제외"]].map(([key, label]) => <div key={key}><span>{label}</span><strong>{preview.summary?.[key] ?? 0}</strong></div>)}</div>
          <div className="online-preview-table-wrap"><table className="online-preview-table online-target-table"><thead><tr><th>상태</th><th>행 번호</th>{COLUMNS.map(([key, label]) => <th key={key}>{label}</th>)}<th>사유</th></tr></thead><tbody>{preview.rows.map((row) => <tr key={row.raw_row_number}>
            <td><span className={`online-preview-badge online-preview-badge-${row.status}`}>{STATUS[row.status]}</span></td><td>{row.raw_row_number}</td>
            {COLUMNS.map(([key]) => <td key={key} title={String(row.data?.[key] ?? "")}>{key === "phone_raw" ? formatPhoneForDisplay(row.data?.[key] || "") : row.data?.[key] || "-"}</td>)}
            <td>{[row.duplicate_reason, ...(row.reasons || [])].filter(Boolean).join(", ") || "-"}</td>
          </tr>)}</tbody></table></div>
        </div>}
        {result && <div className="online-registration-result" role="status"><strong>리콜 대상 등록 완료</strong><span>전체 {result.total}건 · 등록 {result.registered}건 · 정상 {result.normal}건 · 중복 {result.duplicate}건 · 확인 필요 {result.review}건 · 제외 {result.excluded}건</span></div>}
        <footer className="online-upload-footer"><button type="button" className="secondary-button" onClick={onClose} disabled={busy}>닫기</button>{preview && !result && <button type="button" className="primary-action" onClick={commit} disabled={busy}>최종 등록</button>}</footer>
      </section>
    </div>, document.body,
  );
}

export default RecallTargetUploadModal;
