import React from "react";
import useResizableColumns from "../hooks/useResizableColumns.js";

const INSTALL_LIBRARY_COLUMN_WIDTH_STORAGE_KEY = "assetManager.installLibraryTable.columnWidths";
const INSTALL_LIBRARY_COLUMNS = [
  { key: "title", label: "자료명", initialWidth: 260, minWidth: 180 },
  { key: "category", label: "분류", initialWidth: 120, minWidth: 90 },
  { key: "os", label: "OS", initialWidth: 100, minWidth: 80 },
  { key: "version", label: "버전", initialWidth: 100, minWidth: 80 },
  { key: "size", label: "크기", initialWidth: 100, minWidth: 80 },
  { key: "downloads", label: "다운로드", initialWidth: 100, minWidth: 80 },
  { key: "created", label: "등록일", initialWidth: 120, minWidth: 100 },
  { key: "actions", label: "작업", initialWidth: 220, minWidth: 120 },
];

function InstallLibraryList({
  error = "",
  isAdminMode = false,
  isLoading = false,
  items = [],
  onDelete,
  onDownload,
  onEdit,
  onOpenDetail,
}) {
  const { columnWidths, handleColumnResizeStart, tableWidth } = useResizableColumns(
    INSTALL_LIBRARY_COLUMNS,
    INSTALL_LIBRARY_COLUMN_WIDTH_STORAGE_KEY,
    "install-library-column-resizing",
  );

  if (isLoading) {
    return <div className="install-library-empty">설치자료 목록을 불러오는 중입니다.</div>;
  }

  if (error) {
    return <div className="install-library-empty error">{error}</div>;
  }

  if (items.length === 0) {
    return <div className="install-library-empty">등록된 설치자료가 없습니다.</div>;
  }

  return (
    <div className="install-library-table-wrap">
      <table className="install-library-table resizable-data-table" style={{ minWidth: `${tableWidth}px` }}>
        <colgroup>
          {INSTALL_LIBRARY_COLUMNS.map((column) => (
            <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {INSTALL_LIBRARY_COLUMNS.map((column) => (
              <th key={column.key}>
                <span className="resizable-table-heading">{column.label}</span>
                <span
                  aria-hidden="true"
                  className="table-column-resize-handle"
                  onMouseDown={(event) => handleColumnResizeStart(event, column)}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="install-library-title-cell">
                  <div className="install-library-title-line">
                    {Number(item.install_order || 0) > 0 && (
                      <em className="install-library-order-badge">{item.install_order}</em>
                    )}
                    <strong>{item.title}</strong>
                    {item.is_required && <em className="install-library-required-badge">필수</em>}
                  </div>
                  <span>{item.original_filename}</span>
                </div>
              </td>
              <td>{item.category}</td>
              <td>{item.os_type}</td>
              <td>{item.version || "-"}</td>
              <td>{formatBytes(item.file_size)}</td>
              <td>{Number(item.download_count || 0).toLocaleString("ko-KR")}</td>
              <td>{formatDate(item.created_at)}</td>
              <td>
                <div className="install-library-row-actions">
                  <button type="button" className="secondary-button" onClick={() => onDownload?.(item)}>
                    다운로드
                  </button>
                  <button type="button" className="ghost-button" onClick={() => onOpenDetail?.(item)}>
                    안내
                  </button>
                  {isAdminMode && (
                    <>
                      <button type="button" className="ghost-button" onClick={() => onEdit?.(item)}>
                        수정
                      </button>
                      <button type="button" className="danger-ghost-button" onClick={() => onDelete?.(item)}>
                        삭제
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}GB`;
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)}KB`;
  }
  return `${bytes}B`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default InstallLibraryList;
