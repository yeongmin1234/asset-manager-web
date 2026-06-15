import React, { useMemo, useRef, useState } from "react";
import {
  commitAssetExcelImport,
  downloadAssetImportTemplate,
  previewAssetExcelImport,
} from "../api/client.js";

function AssetExcelTools({ onImportCommitted, onExportExcel, isExporting = false, exportError = "" }) {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewResult, setPreviewResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [toolState, setToolState] = useState({
    isTemplateDownloading: false,
    isPreviewing: false,
    isCommitting: false,
  });

  const validRows = useMemo(
    () => (previewResult?.rows || []).filter((row) => row.is_valid && row.data),
    [previewResult],
  );
  const errorRows = useMemo(
    () => (previewResult?.rows || []).filter((row) => !row.is_valid),
    [previewResult],
  );

  const handleTemplateDownload = async () => {
    setToolState((current) => ({ ...current, isTemplateDownloading: true }));
    setError("");
    setMessage("");

    try {
      const { blob, filename } = await downloadAssetImportTemplate();
      downloadBlob(blob, filename || "asset_import_template.xlsx");
    } catch (downloadError) {
      setError(downloadError.message);
    } finally {
      setToolState((current) => ({ ...current, isTemplateDownloading: false }));
    }
  };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files?.[0] || null);
    setPreviewResult(null);
    setMessage("");
    setError("");
  };

  const handlePreview = async () => {
    if (!selectedFile) {
      setError("미리보기할 엑셀 파일을 선택해주세요.");
      return;
    }

    setToolState((current) => ({ ...current, isPreviewing: true }));
    setPreviewResult(null);
    setMessage("");
    setError("");

    try {
      setPreviewResult(await previewAssetExcelImport(selectedFile));
    } catch (previewError) {
      setError(previewError.message);
    } finally {
      setToolState((current) => ({ ...current, isPreviewing: false }));
    }
  };

  const handleCommit = async () => {
    if (validRows.length === 0) {
      return;
    }

    setToolState((current) => ({ ...current, isCommitting: true }));
    setMessage("");
    setError("");

    try {
      const result = await commitAssetExcelImport(validRows);
      if (result.errors?.length) {
        setError(`일부 행을 등록하지 못했습니다. 등록 ${result.created_count || 0}건`);
        setPreviewResult({
          total_rows: result.errors.length,
          valid_rows: 0,
          error_rows: result.errors.length,
          rows: result.errors,
        });
      } else {
        setMessage(`${result.created_count || 0}건을 등록했습니다.`);
        setPreviewResult(null);
        setSelectedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
      await onImportCommitted?.();
    } catch (commitError) {
      setError(commitError.message);
    } finally {
      setToolState((current) => ({ ...current, isCommitting: false }));
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewResult(null);
    setMessage("");
    setError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <section className="excel-tools" aria-labelledby="excel-tools-title">
      <div className="excel-tools-heading">
        <div>
          <h3 id="excel-tools-title">엑셀 관리</h3>
          <p>양식을 내려받아 작성한 뒤 업로드해 검증합니다.</p>
        </div>
        <div className="excel-heading-actions">
          {onExportExcel && (
            <button
              type="button"
              className="secondary-button export-button"
              onClick={onExportExcel}
              disabled={isExporting}
            >
              {isExporting ? "다운로드 중..." : "엑셀 내보내기"}
            </button>
          )}
          <button
            type="button"
            className="secondary-button export-button"
            onClick={handleTemplateDownload}
            disabled={toolState.isTemplateDownloading}
          >
            {toolState.isTemplateDownloading ? "다운로드 중..." : "엑셀 양식 다운로드"}
          </button>
        </div>
      </div>

      <div className="excel-tools-controls">
        <label className="field excel-file-field">
          <span>엑셀 파일 선택</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            onChange={handleFileChange}
          />
        </label>
        <div className="excel-tools-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={handlePreview}
            disabled={!selectedFile || toolState.isPreviewing}
          >
            {toolState.isPreviewing ? "검증 중..." : "업로드 미리보기"}
          </button>
          <button type="button" className="secondary-button" onClick={handleReset}>
            초기화
          </button>
          <button
            type="button"
            className="primary-action"
            onClick={handleCommit}
            disabled={validRows.length === 0 || toolState.isCommitting}
          >
            {toolState.isCommitting ? "등록 중..." : "정상 행 일괄 등록"}
          </button>
        </div>
      </div>

      {selectedFile && <p className="excel-file-name">선택 파일: {selectedFile.name}</p>}
      {message && <div className="inline-success">{message}</div>}
      {error && <div className="inline-alert">{error}</div>}
      {exportError && (
        <div className="inline-alert">
          엑셀 파일을 다운로드하지 못했습니다. {exportError}
        </div>
      )}

      {previewResult && (
        <div className="excel-preview">
          <div className="excel-preview-summary">
            <div className="excel-summary-card">
              <span>전체 행</span>
              <strong>{previewResult.total_rows || 0}</strong>
            </div>
            <div className="excel-summary-card excel-summary-valid">
              <span>정상 행</span>
              <strong>{previewResult.valid_rows || 0}</strong>
            </div>
            <div className="excel-summary-card excel-summary-error">
              <span>오류 행</span>
              <strong>{previewResult.error_rows || 0}</strong>
            </div>
          </div>

          <div className={errorRows.length > 0 ? "excel-preview-note warning" : "excel-preview-note"}>
            {validRows.length > 0
              ? `정상 ${validRows.length}행만 일괄 등록할 수 있습니다.`
              : "등록 가능한 정상 행이 없습니다. 오류를 수정한 뒤 다시 업로드해주세요."}
          </div>

          <div className="excel-preview-table-wrap">
            <table className="excel-preview-table">
              <thead>
                <tr>
                  <th>행</th>
                  <th>상태</th>
                  <th>제품명</th>
                  <th>분류</th>
                  <th>부서(사용자명)</th>
                  <th>시리얼번호</th>
                  <th>오류 사유</th>
                </tr>
              </thead>
              <tbody>
                {previewResult.rows.map((row) => (
                  <tr key={row.row_number} className={row.is_valid ? "" : "excel-row-error"}>
                    <td>{row.row_number}</td>
                    <td>
                      <span className={row.is_valid ? "excel-status-pill valid" : "excel-status-pill error"}>
                        {row.is_valid ? "정상" : "오류"}
                      </span>
                    </td>
                    <td>{row.data?.name || "-"}</td>
                    <td>{row.data?.category_name || "-"}</td>
                    <td>{row.data?.department_name || "-"}</td>
                    <td>{row.data?.serial_number || "-"}</td>
                    <td>
                      {row.errors?.length ? (
                        <ul className="excel-error-list">
                          {row.errors.map((rowError) => (
                            <li key={rowError}>{rowError}</li>
                          ))}
                        </ul>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default AssetExcelTools;
