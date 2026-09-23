import useDownloadStatus from "../hooks/useDownloadStatus.js";
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteAttachment,
  downloadAttachment,
  getAttachments,
  previewAttachment,
  uploadAttachment,
} from "../api/client.js";
import {
  ATTACHMENT_ACCEPT,
  getAttachmentExtension,
  validateAttachmentFile,
} from "../utils/attachmentRules.js";

function AttachmentPanel({ canManage = false, entityId, entityType, title = "첨부파일" }) {
  const downloadBusy = useDownloadStatus();
  const [items, setItems] = useState([]);
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [state, setState] = useState({ error: "", isDragging: false, isLoading: false, isUploading: false, message: "" });
  const fileInputRef = useRef(null);

  const loadAttachments = useCallback(async () => {
    if (!entityType || !entityId) {
      setItems([]);
      return;
    }
    setState((current) => ({ ...current, error: "", isLoading: true }));
    try {
      const data = await getAttachments({ entity_type: entityType, entity_id: entityId });
      setItems(Array.isArray(data) ? data : []);
      setState((current) => ({ ...current, isLoading: false }));
    } catch (error) {
      setItems([]);
      setState((current) => ({ ...current, error: error.message, isLoading: false }));
    }
  }, [entityId, entityType]);

  useEffect(() => {
    loadAttachments();
  }, [loadAttachments]);

  const handleFileSelect = (file) => {
    setState((current) => ({ ...current, error: "", message: "" }));
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const validationError = validateFile(file);
    if (validationError) {
      setSelectedFile(null);
      setState((current) => ({ ...current, error: validationError }));
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!canManage || state.isUploading) {
      return;
    }
    const validationError = validateAttachmentFile(selectedFile);
    if (validationError) {
      setState((current) => ({ ...current, error: validationError }));
      return;
    }
    setState((current) => ({ ...current, error: "", isUploading: true, message: "" }));
    try {
      await uploadAttachment({
        entity_type: entityType,
        entity_id: entityId,
        file: selectedFile,
        description,
      });
      setSelectedFile(null);
      setDescription("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setState((current) => ({ ...current, isUploading: false, message: "첨부파일을 업로드했습니다." }));
      await loadAttachments();
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, isUploading: false }));
    }
  };

  const handleDownload = async (item) => {
    try {
      await downloadAttachment(item.id);
    } catch (error) {
      setState((current) => ({ ...current, error: error.message }));
    }
  };

  const handlePreview = async (item) => {
    try {
      await previewAttachment(item.id);
    } catch (error) {
      setState((current) => ({ ...current, error: error.message }));
    }
  };

  const handleDelete = async (item) => {
    if (!window.confirm(`${item.original_filename} 첨부파일을 삭제하시겠습니까?`)) {
      return;
    }
    try {
      await deleteAttachment(item.id);
      setState((current) => ({ ...current, message: "첨부파일을 삭제했습니다." }));
      await loadAttachments();
    } catch (error) {
      setState((current) => ({ ...current, error: error.message }));
    }
  };

  return (
    <section className="attachment-panel">
      <div className="attachment-panel-heading">
        <h3>{title} {items.length ? <span>{items.length}개</span> : null}</h3>
        <small>PDF, JPG/JPEG/PNG/GIF/WEBP/BMP, DOC/DOCX/XLS/XLSX/PPT/PPTX, TXT, ZIP · 최대 20MB</small>
      </div>

      {canManage ? (
        <form
          className={state.isDragging ? "attachment-upload-zone dragging" : "attachment-upload-zone"}
          onSubmit={handleUpload}
          onDragOver={(event) => {
            event.preventDefault();
            setState((current) => ({ ...current, isDragging: true }));
          }}
          onDragLeave={() => setState((current) => ({ ...current, isDragging: false }))}
          onDrop={(event) => {
            event.preventDefault();
            setState((current) => ({ ...current, isDragging: false }));
            handleFileSelect(event.dataTransfer.files?.[0]);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ATTACHMENT_ACCEPT}
            onChange={(event) => handleFileSelect(event.target.files?.[0])}
          />
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="파일 설명"
            maxLength={500}
          />
          <button type="submit" className="secondary-button" disabled={!selectedFile || state.isUploading}>
            {state.isUploading ? "업로드 중" : "업로드"}
          </button>
          <span>{selectedFile ? selectedFile.name : "파일을 선택하거나 끌어오세요."}</span>
        </form>
      ) : null}

      {state.error ? <p className="attachment-error">{state.error}</p> : null}
      {state.message ? <p className="attachment-message">{state.message}</p> : null}

      <div className="attachment-list">
        {state.isLoading ? (
          <div className="attachment-empty">첨부파일을 불러오는 중입니다.</div>
        ) : items.length === 0 ? (
          <div className="attachment-empty">첨부파일이 없습니다.</div>
        ) : items.map((item) => (
          <div className="attachment-item" key={item.id}>
            <span className="attachment-file-icon">{getFileIcon(item.original_filename)}</span>
            <div className="attachment-file-main">
              <strong title={item.original_filename}>{item.original_filename}</strong>
              <p>
                {formatFileSize(item.file_size)} · {item.uploader_name || "-"} · {formatDate(item.created_at)}
                {item.description ? ` · ${item.description}` : ""}
              </p>
            </div>
            <div className="attachment-actions">
              {canPreview(item) ? (
                <button type="button" className="ghost-button" disabled={downloadBusy} onClick={() => handlePreview(item)}>{downloadBusy ? "준비 중…" : "미리보기"}</button>
              ) : null}
              <button type="button" className="ghost-button" disabled={downloadBusy} onClick={() => handleDownload(item)}>{downloadBusy ? "준비 중…" : "다운로드"}</button>
              {canManage ? (
                <button type="button" className="danger-outline-button" onClick={() => handleDelete(item)}>삭제</button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function validateFile(file) {
  return validateAttachmentFile(file);
}

function canPreview(item) {
  return [
    "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp", "image/x-ms-bmp",
  ].includes(String(item.mime_type || "").toLowerCase());
}

function getExtension(filename) {
  return getAttachmentExtension(filename);
}

function getFileIcon(filename) {
  const extension = getExtension(filename);
  if (["png", "jpg", "jpeg", "gif", "webp", "bmp"].includes(extension)) return "IMG";
  if (extension === "pdf") return "PDF";
  if (["xlsx", "xls"].includes(extension)) return "XLS";
  if (["docx", "doc"].includes(extension)) return "DOC";
  if (["pptx", "ppt"].includes(extension)) return "PPT";
  if (extension === "zip") return "ZIP";
  return "TXT";
}

function formatFileSize(value) {
  const size = Number(value || 0);
  if (size >= 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(1)}MB`;
  }
  if (size >= 1024) {
    return `${Math.round(size / 1024)}KB`;
  }
  return `${size}B`;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString("ko-KR");
}


export default AttachmentPanel;
