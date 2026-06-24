import React from "react";

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
      <table className="install-library-table">
        <thead>
          <tr>
            <th>자료명</th>
            <th>분류</th>
            <th>OS</th>
            <th>버전</th>
            <th>크기</th>
            <th>다운로드</th>
            <th>등록일</th>
            <th>작업</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="install-library-title-cell">
                  <strong>{item.title}</strong>
                  <span>{item.original_filename}</span>
                  <div className="install-library-badge-row">
                    {item.is_required && <em className="install-library-required-badge">필수</em>}
                    {Number(item.install_order || 0) > 0 && (
                      <em className="install-library-order-badge">{item.install_order}순서</em>
                    )}
                  </div>
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
