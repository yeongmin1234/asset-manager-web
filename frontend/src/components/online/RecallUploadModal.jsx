import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { previewRecallApplicationExcel } from "../../api/client.js";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const SUMMARY_ITEMS = [
  ["total_rows", "전체 행"],
  ["valid", "정상"],
  ["duplicate", "중복"],
  ["error", "오류"],
  ["review", "확인 필요"],
  ["excluded", "제외 행"],
];
const STATUS_LABELS = {
  valid: "정상", duplicate: "중복", error: "오류", review: "확인 필요", excluded: "제외",
};
const ISSUE_LABELS = {
  DUPLICATE_SERIAL: "시리얼번호 중복",
  DUPLICATE_PHONE: "연락처 중복",
  INVALID_PHONE: "연락처 오류",
  MISSING_REQUIRED: "필수값 누락",
  INVALID_QUANTITY: "수량 오류",
  INVALID_DATE: "날짜 오류",
  REVIEW_REQUIRED: "확인 필요",
};
const FIELD_LABELS = {
  customer_name: "고객명", phone_original: "연락처", address: "주소",
  serial_number: "시리얼번호", quantity: "수량", application_date: "신청일자", pickup_date: "회수 일자",
};

function displayValue(row, field, sourceHeader) {
  const value = row.data?.[field] ?? row.raw_data?.[sourceHeader];
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function issueDescription(row) {
  if (row.status === "excluded") return row.row_kind === "blank" ? "빈 행" : "업무 안내 행";
  if (!row.issues?.length) return "정상";
  return row.issues.map((issue) => {
    const label = ISSUE_LABELS[issue.code] || issue.message || issue.code;
    const field = FIELD_LABELS[issue.field];
    const source = issue.source === "file" ? ` · 파일 ${issue.matched_row_number}행` :
      issue.source === "existing" ? ` · 기존 데이터${issue.existing_status ? ` (${issue.existing_status})` : ""}` : "";
    return `${label}${field ? ` (${field})` : ""}${source}`;
  }).join(" / ");
}

function RecallPreviewTable({ rows }) {
  return (
    <div className="online-preview-table-wrap">
      <table className="online-preview-table">
        <thead><tr>
          {[
            "상태", "행 번호", "신청일자", "수량", "고객명", "연락처", "주소", "메모",
            "시리얼번호", "LOT 번호", "회수 동의", "회수 일자", "대체 필터 출고 동의", "검증 결과",
          ].map((header) => <th scope="col" key={header}>{header}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.raw_row_number}>
              <td><span className={`online-preview-badge online-preview-badge-${row.status}`}>{STATUS_LABELS[row.status] || row.status}</span></td>
              <td>{row.raw_row_number}</td>
              <td>{displayValue(row, "application_date", "신청일자")}</td>
              <td>{displayValue(row, "quantity", "수량")}</td>
              <td>{displayValue(row, "customer_name", "성함")}</td>
              <td title={row.data?.phone_normalized ? `비교용: ${row.data.phone_normalized}` : undefined}>
                {displayValue(row, "phone_original", "*연락처")}
              </td>
              <td>{displayValue(row, "address", "주소지")}</td>
              <td>{displayValue(row, "memo", "메모")}</td>
              <td>{displayValue(row, "serial_number", "*시리얼번호")}</td>
              <td>{displayValue(row, "lot_number", "LOT 번호")}</td>
              <td>{displayValue(row, "pickup_agreement", "기존 필터 회수 동의")}</td>
              <td>{displayValue(row, "pickup_date", "회수 일자")}</td>
              <td>{displayValue(row, "replacement_shipping_agreement", "대체 필터 출고 동의")}</td>
              <td className="online-preview-issues">{issueDescription(row)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecallUploadModal({ mode, onClose }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef(null);
  const isApplication = mode === "application";

  useEffect(() => {
    if (isApplication) fileInputRef.current?.focus();
  }, [isApplication]);

  useEffect(() => {
    const handleEscape = (event) => { if (event.key === "Escape" && !isLoading) onClose(); };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isApplication, isLoading, onClose]);

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0] || null;
    setPreview(null);
    setFile(null);
    setError("");
    if (!selected) return;
    if (!/\.xlsx$/i.test(selected.name)) {
      setError(".xlsx 파일만 선택할 수 있습니다.");
      event.target.value = "";
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      setError("Excel 파일은 최대 5MB까지 미리볼 수 있습니다.");
      event.target.value = "";
      return;
    }
    setFile(selected);
  };

  const handlePreview = async (event) => {
    event.preventDefault();
    if (!file || isLoading) return;
    setIsLoading(true);
    setError("");
    setPreview(null);
    try {
      setPreview(await previewRecallApplicationExcel(file));
    } catch (caught) {
      setError(caught?.message || "Excel 미리보기를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return createPortal(
    <div className="online-upload-backdrop" onMouseDown={() => { if (!isLoading) onClose(); }}>
      <section className="online-upload-modal" role="dialog" aria-modal="true" aria-labelledby="online-upload-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="online-upload-header">
          <div>
            <h2 id="online-upload-title">{isApplication ? "접수 데이터 등록" : "리콜 대상 등록"}</h2>
            {isApplication && <p>Excel 신청 데이터를 검증하고 등록 전 결과를 확인합니다.</p>}
          </div>
          <button type="button" className="secondary-button" onClick={onClose} disabled={isLoading} aria-label="닫기">닫기</button>
        </header>

        {isApplication ? (
          <>
            <form className="online-upload-form" onSubmit={handlePreview}>
              <label htmlFor="online-application-file">접수 데이터 Excel (.xlsx, 최대 5MB)</label>
              <div className="online-upload-controls">
                <input id="online-application-file" ref={fileInputRef} type="file" accept=".xlsx" onChange={handleFileChange} disabled={isLoading} />
                <button type="submit" className="primary-action" disabled={!file || isLoading}>{isLoading ? "분석 중..." : "미리보기"}</button>
              </div>
            </form>
            {error && <p className="online-upload-error" role="alert">{error}</p>}
            {preview && (
              <div className="online-preview-result">
                <p className="online-preview-sheet">시트: {preview.sheet_name} · 전체 행은 헤더를 제외한 행 수입니다.</p>
                <div className="online-preview-summary" aria-label="Excel 미리보기 요약">
                  {SUMMARY_ITEMS.map(([key, label]) => (
                    <div key={key}><span>{label}</span><strong>{preview.summary?.[key] ?? 0}</strong></div>
                  ))}
                </div>
                <RecallPreviewTable rows={preview.rows || []} />
              </div>
            )}
          </>
        ) : (
          <p className="online-upload-notice">리콜 대상 Raw Data Excel 형식은 추후 확정 예정입니다.</p>
        )}

        <footer className="online-upload-footer">
          <button type="button" className="secondary-button" onClick={onClose} disabled={isLoading}>닫기</button>
          {isApplication && <button type="button" className="primary-action" disabled title="다음 Phase에서 지원 예정">최종 등록</button>}
        </footer>
      </section>
    </div>,
    document.body,
  );
}

export default RecallUploadModal;
