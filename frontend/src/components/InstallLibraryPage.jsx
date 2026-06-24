import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createInstallFile,
  deleteInstallFile,
  downloadInstallFile,
  getInstallFileSummary,
  getInstallFiles,
  updateInstallFile,
  verifyAdminPassword,
} from "../api/client.js";
import InstallChecklistPanel from "./InstallChecklistPanel.jsx";
import InstallLibraryDetail from "./InstallLibraryDetail.jsx";
import InstallLibraryForm from "./InstallLibraryForm.jsx";
import InstallLibraryList from "./InstallLibraryList.jsx";

const INITIAL_FILTERS = {
  keyword: "",
  category: "",
  os_type: "",
  is_required: "",
};

const INITIAL_SUMMARY = {
  total_count: 0,
  required_count: 0,
  total_size: 0,
  total_download_count: 0,
};

const CATEGORY_OPTIONS = ["필수 프로그램", "드라이버", "업무 도구", "보안", "문서", "스크립트", "기타"];
const OS_OPTIONS = ["전체", "Windows", "macOS", "Linux", "NAS", "기타"];

function InstallLibraryPage() {
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [listState, setListState] = useState({ error: "", isLoading: false });
  const [adminPassword, setAdminPassword] = useState("");
  const [adminMode, setAdminMode] = useState({ error: "", isEnabled: false, isVerifying: false });
  const [formState, setFormState] = useState({
    error: "",
    initialItem: null,
    isOpen: false,
    isSubmitting: false,
  });
  const [detailItem, setDetailItem] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [toastMessage, setToastMessage] = useState("");

  const queryFilters = useMemo(
    () => ({
      keyword: filters.keyword.trim(),
      category: filters.category,
      os_type: filters.os_type,
      is_required: filters.is_required,
    }),
    [filters],
  );

  const loadInstallLibrary = useCallback(async () => {
    setListState({ error: "", isLoading: true });
    try {
      const [listResult, summaryResult] = await Promise.all([
        getInstallFiles(queryFilters),
        getInstallFileSummary(),
      ]);
      setItems(Array.isArray(listResult?.items) ? listResult.items : []);
      setSummary({ ...INITIAL_SUMMARY, ...(summaryResult || {}) });
      setListState({ error: "", isLoading: false });
    } catch (error) {
      setItems([]);
      setSummary(INITIAL_SUMMARY);
      setListState({ error: error.message, isLoading: false });
    }
  }, [queryFilters]);

  useEffect(() => {
    loadInstallLibrary();
  }, [loadInstallLibrary]);

  const handleFilterChange = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }));
  };

  const handleAdminVerify = async (event) => {
    event.preventDefault();
    setAdminMode({ error: "", isEnabled: false, isVerifying: true });
    try {
      await verifyAdminPassword(adminPassword);
      setAdminMode({ error: "", isEnabled: true, isVerifying: false });
      setToastMessage("관리자 모드가 활성화되었습니다.");
    } catch (error) {
      setAdminMode({ error: "관리자 비밀번호를 확인해 주세요.", isEnabled: false, isVerifying: false });
    }
  };

  const handleAdminClear = () => {
    setAdminPassword("");
    setAdminMode({ error: "", isEnabled: false, isVerifying: false });
    setToastMessage("관리자 모드를 종료했습니다.");
  };

  const handleFormSubmit = async (payload) => {
    if (!adminMode.isEnabled || !adminPassword) {
      setFormState((current) => ({ ...current, error: "관리자 인증 후 저장할 수 있습니다." }));
      return;
    }
    setFormState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      const requestPayload = { ...payload, admin_password: adminPassword };
      if (formState.initialItem?.id) {
        await updateInstallFile(formState.initialItem.id, requestPayload);
      } else {
        await createInstallFile(requestPayload);
      }
      setFormState({ error: "", initialItem: null, isOpen: false, isSubmitting: false });
      setToastMessage("설치자료가 저장되었습니다.");
      await loadInstallLibrary();
    } catch (error) {
      setFormState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    try {
      await deleteInstallFile(deleteTarget.id, adminPassword);
      setDeleteTarget(null);
      setToastMessage("설치자료가 삭제되었습니다.");
      await loadInstallLibrary();
    } catch (error) {
      setToastMessage(error.message);
    }
  };

  const handleDownload = async (item) => {
    try {
      const { blob, filename } = await downloadInstallFile(item.id);
      downloadBlob(blob, filename || item.original_filename || "install-file");
      await loadInstallLibrary();
    } catch (error) {
      setToastMessage(error.message);
    }
  };

  return (
    <section className="install-library-page" aria-labelledby="install-library-title">
      <div className="install-library-hero">
        <div>
          <span className="section-kicker">Internal Install Library</span>
          <h2 id="install-library-title">설치자료실</h2>
          <p>USB로 들고 다니던 설치 파일을 내부 웹에서 등록, 조회, 다운로드합니다.</p>
        </div>
        <button
          type="button"
          disabled={!adminMode.isEnabled}
          onClick={() => setFormState({ error: "", initialItem: null, isOpen: true, isSubmitting: false })}
        >
          설치자료 등록
        </button>
      </div>

      <div className="install-library-summary-grid">
        <SummaryCard label="등록 자료" value={`${summary.total_count}개`} />
        <SummaryCard label="필수 자료" value={`${summary.required_count}개`} />
        <SummaryCard label="총 용량" value={formatBytes(summary.total_size)} />
        <SummaryCard label="다운로드" value={`${Number(summary.total_download_count || 0).toLocaleString("ko-KR")}회`} />
      </div>

      <section className="install-library-admin-panel">
        <div>
          <strong>관리자 모드</strong>
          <p>등록, 수정, 삭제는 관리자 비밀번호 확인 후 현재 화면에서만 사용할 수 있습니다.</p>
          {adminMode.error && <span>{adminMode.error}</span>}
        </div>
        <form onSubmit={handleAdminVerify}>
          <input
            type="password"
            value={adminPassword}
            autoComplete="current-password"
            placeholder="관리자 비밀번호"
            disabled={adminMode.isVerifying || adminMode.isEnabled}
            onChange={(event) => setAdminPassword(event.target.value)}
          />
          {adminMode.isEnabled ? (
            <button type="button" className="secondary-button" onClick={handleAdminClear}>
              관리자 모드 종료
            </button>
          ) : (
            <button type="submit" className="secondary-button" disabled={adminMode.isVerifying || !adminPassword}>
              인증
            </button>
          )}
        </form>
      </section>

      <section className="install-library-controls">
        <label>
          <span>검색</span>
          <input value={filters.keyword} placeholder="자료명, 설명, 파일명" onChange={(event) => handleFilterChange("keyword", event.target.value)} />
        </label>
        <label>
          <span>분류</span>
          <select value={filters.category} onChange={(event) => handleFilterChange("category", event.target.value)}>
            <option value="">전체</option>
            {CATEGORY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </label>
        <label>
          <span>OS</span>
          <select value={filters.os_type} onChange={(event) => handleFilterChange("os_type", event.target.value)}>
            <option value="">전체</option>
            {OS_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </label>
        <label>
          <span>필수 여부</span>
          <select value={filters.is_required} onChange={(event) => handleFilterChange("is_required", event.target.value)}>
            <option value="">전체</option>
            <option value="true">필수</option>
            <option value="false">선택</option>
          </select>
        </label>
        <button type="button" className="secondary-button" onClick={() => setFilters(INITIAL_FILTERS)}>
          초기화
        </button>
        <button type="button" className="secondary-button" onClick={loadInstallLibrary}>
          새로고침
        </button>
      </section>

      {toastMessage && (
        <div className="install-library-toast">
          <span>{toastMessage}</span>
          <button type="button" className="ghost-button" onClick={() => setToastMessage("")}>닫기</button>
        </div>
      )}

      <div className="install-library-content-grid">
        <section className="content-panel install-library-list-panel">
          <InstallLibraryList
            error={listState.error}
            isAdminMode={adminMode.isEnabled}
            isLoading={listState.isLoading}
            items={items}
            onDelete={setDeleteTarget}
            onDownload={handleDownload}
            onEdit={(item) => setFormState({ error: "", initialItem: item, isOpen: true, isSubmitting: false })}
            onOpenDetail={setDetailItem}
          />
        </section>
        <InstallChecklistPanel items={items} />
      </div>

      <InstallLibraryForm
        error={formState.error}
        initialItem={formState.initialItem}
        isOpen={formState.isOpen}
        isSubmitting={formState.isSubmitting}
        onClose={() => setFormState({ error: "", initialItem: null, isOpen: false, isSubmitting: false })}
        onSubmit={handleFormSubmit}
      />
      <InstallLibraryDetail item={detailItem} onClose={() => setDetailItem(null)} />
      {deleteTarget && (
        <div className="modal-backdrop install-library-modal-backdrop" role="presentation">
          <section className="install-library-delete-modal" role="dialog" aria-modal="true" aria-labelledby="install-library-delete-title">
            <h3 id="install-library-delete-title">설치자료 삭제</h3>
            <p>{deleteTarget.title} 자료를 삭제합니다. 목록에서 숨김 처리되고 저장 파일도 제거됩니다.</p>
            <div className="install-library-form-actions">
              <button type="button" className="secondary-button" onClick={() => setDeleteTarget(null)}>
                취소
              </button>
              <button type="button" className="danger-button" onClick={handleDelete}>
                삭제
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="install-library-summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
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

export default InstallLibraryPage;
