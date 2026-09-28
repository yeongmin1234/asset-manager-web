import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { commitRecallApplicationExcel, previewRecallApplicationExcel } from "../../api/client.js";
import { formatPhoneForDisplay } from "./onlineDisplayUtils.js";

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
const PREVIEW_COLUMNS = [
  ["선택", "select"],
  ["상태", "status"],
  ["행 번호", "row-number"],
  ["신청일자", "date"],
  ["수량", "quantity"],
  ["고객명", "customer"],
  ["연락처", "phone"],
  ["주소", "address"],
  ["메모", "memo"],
  ["시리얼번호", "serial"],
  ["LOT 번호", "lot"],
  ["회수 동의", "agreement"],
  ["회수 일자", "date"],
  ["대체 필터 출고 동의", "agreement"],
  ["검증 결과", "issues"],
];

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

function RecallPreviewTable({ rows, selectedRows, onToggle, onToggleAll }) {
  const selectableRows = rows.filter((row) => row.status === "valid" || row.status === "review");
  const allSelected = selectableRows.length > 0 && selectableRows.every((row) => selectedRows.has(row.raw_row_number));
  return (
    <div className="online-preview-table-wrap">
      <table className="online-preview-table">
        <colgroup>
          {PREVIEW_COLUMNS.map(([header, column], index) => (
            <col className={`online-preview-column-${column}`} key={`${header}-${index}`} />
          ))}
        </colgroup>
        <thead><tr>
          {PREVIEW_COLUMNS.map(([header, column], index) => (
            <th className={`online-preview-cell-${column}`} scope="col" key={`${header}-${index}`}>
              {column === "select" ? (
                <input type="checkbox" checked={allSelected} onChange={(event) => onToggleAll(event.target.checked)} aria-label="등록 가능한 행 전체 선택" />
              ) : header}
            </th>
          ))}
        </tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.raw_row_number}>
              <td className="online-preview-cell-select">
                <input
                  type="checkbox"
                  checked={selectedRows.has(row.raw_row_number)}
                  disabled={row.status !== "valid" && row.status !== "review"}
                  onChange={() => onToggle(row.raw_row_number)}
                  aria-label={`${row.raw_row_number}행 등록 선택`}
                  title={row.status === "review" ? "확인 필요 행은 내용을 검토한 뒤 직접 선택해주세요." : undefined}
                />
              </td>
              <td className="online-preview-cell-status"><span className={`online-preview-badge online-preview-badge-${row.status}`}>{STATUS_LABELS[row.status] || row.status}</span></td>
              <td className="online-preview-cell-row-number">{row.raw_row_number}</td>
              <td className="online-preview-cell-date">{displayValue(row, "application_date", "신청일자")}</td>
              <td className="online-preview-cell-quantity">{displayValue(row, "quantity", "수량")}</td>
              <td className="online-preview-cell-customer">{displayValue(row, "customer_name", "성함")}</td>
              <td className="online-preview-cell-phone" title={row.data?.phone_normalized ? `비교용: ${row.data.phone_normalized}` : undefined}>
                {formatPhoneForDisplay(displayValue(row, "phone_original", "*연락처"))}
              </td>
              <td className="online-preview-cell-address" title={displayValue(row, "address", "주소지")}>{displayValue(row, "address", "주소지")}</td>
              <td className="online-preview-cell-memo" title={displayValue(row, "memo", "메모")}>{displayValue(row, "memo", "메모")}</td>
              <td className="online-preview-cell-serial">{displayValue(row, "serial_number", "*시리얼번호")}</td>
              <td className="online-preview-cell-lot">{displayValue(row, "lot_number", "LOT 번호")}</td>
              <td className="online-preview-cell-agreement">{displayValue(row, "pickup_agreement", "기존 필터 회수 동의")}</td>
              <td className="online-preview-cell-date">{displayValue(row, "pickup_date", "회수 일자")}</td>
              <td className="online-preview-cell-agreement">{displayValue(row, "replacement_shipping_agreement", "대체 필터 출고 동의")}</td>
              <td className="online-preview-cell-issues">{issueDescription(row)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecallUploadModal({ mode, onClose, onRegistered }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [registrationResult, setRegistrationResult] = useState(null);
  const fileInputRef = useRef(null);
  const isApplication = mode === "application";
  const isBusy = isLoading || isCommitting;

  useEffect(() => {
    if (isApplication) fileInputRef.current?.focus();
  }, [isApplication]);

  useEffect(() => {
    const handleEscape = (event) => { if (event.key === "Escape" && !isBusy) onClose(); };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isApplication, isBusy, onClose]);

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0] || null;
    setPreview(null);
    setSelectedRows(new Set());
    setRegistrationResult(null);
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
      const result = await previewRecallApplicationExcel(file);
      setPreview(result);
      setSelectedRows(new Set(
        (result.rows || []).filter((row) => row.status === "valid").map((row) => row.raw_row_number),
      ));
    } catch (caught) {
      setError(caught?.message || "Excel 미리보기를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggle = (rowNumber) => {
    setSelectedRows((current) => {
      const next = new Set(current);
      if (next.has(rowNumber)) next.delete(rowNumber);
      else next.add(rowNumber);
      return next;
    });
  };

  const handleToggleAll = (checked) => {
    const selectable = (preview?.rows || [])
      .filter((row) => row.status === "valid" || row.status === "review")
      .map((row) => row.raw_row_number);
    setSelectedRows(checked ? new Set(selectable) : new Set());
  };

  const handleCommit = async () => {
    if (!file || selectedRows.size === 0 || isBusy) return;
    setIsCommitting(true);
    setError("");
    setRegistrationResult(null);
    try {
      const result = await commitRecallApplicationExcel(file, Array.from(selectedRows).sort((a, b) => a - b));
      setRegistrationResult(result);
      await onRegistered?.(result);
    } catch (caught) {
      setError(caught?.message || "접수 데이터를 등록하지 못했습니다.");
    } finally {
      setIsCommitting(false);
    }
  };

  return createPortal(
    <div className="online-upload-backdrop" onMouseDown={() => { if (!isBusy) onClose(); }}>
      <section className="online-upload-modal" role="dialog" aria-modal="true" aria-labelledby="online-upload-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="online-upload-header">
          <div>
            <h2 id="online-upload-title">{isApplication ? "접수 데이터 등록" : "리콜 대상 등록"}</h2>
            {isApplication && <p>Excel 신청 데이터를 검증하고 등록 전 결과를 확인합니다.</p>}
          </div>
          <button type="button" className="secondary-button" onClick={onClose} disabled={isBusy} aria-label="닫기">닫기</button>
        </header>

        {isApplication ? (
          <>
            <form className="online-upload-form" onSubmit={handlePreview}>
              <label htmlFor="online-application-file">접수 데이터 Excel (.xlsx, 최대 5MB)</label>
              <div className="online-upload-controls">
                <input id="online-application-file" ref={fileInputRef} type="file" accept=".xlsx" onChange={handleFileChange} disabled={isBusy} />
                <button type="submit" className="primary-action" disabled={!file || isBusy}>{isLoading ? "분석 중..." : "미리보기"}</button>
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
                <p className="online-preview-selection">정상 행은 기본 선택됩니다. 확인 필요 행은 내용을 검토한 뒤 직접 선택해주세요. · 선택 {selectedRows.size}건</p>
                <RecallPreviewTable rows={preview.rows || []} selectedRows={selectedRows} onToggle={handleToggle} onToggleAll={handleToggleAll} />
              </div>
            )}
            {registrationResult && (
              <div className="online-registration-result" role="status">
                <strong>등록 처리가 완료되었습니다.</strong>
                <span>신규 {registrationResult.registered ?? 0}건</span>
                <span>중복 {registrationResult.duplicate ?? 0}건</span>
                <span>등록 제외 {registrationResult.rejected ?? 0}건</span>
                <span>확인 필요 미선택 {registrationResult.unselected_review ?? 0}건</span>
              </div>
            )}
          </>
        ) : (
          <p className="online-upload-notice">리콜 대상 Raw Data Excel 형식은 추후 확정 예정입니다.</p>
        )}

        <footer className="online-upload-footer">
          <button type="button" className="secondary-button" onClick={onClose} disabled={isBusy}>닫기</button>
          {isApplication && (
            <button type="button" className="primary-action" disabled={selectedRows.size === 0 || isBusy || Boolean(registrationResult)} onClick={handleCommit}>
              {isCommitting ? "등록 중..." : `최종 등록${selectedRows.size ? ` (${selectedRows.size})` : ""}`}
            </button>
          )}
        </footer>
      </section>
    </div>,
    document.body,
  );
}

export default RecallUploadModal;
