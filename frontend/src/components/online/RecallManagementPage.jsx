import React, { useCallback, useEffect, useState } from "react";
import { bulkChangeRecallApplications, getRecallApplications, getRecallApplicationSummary } from "../../api/client.js";
import RecallFilters from "./RecallFilters.jsx";
import RecallSummaryCards from "./RecallSummaryCards.jsx";
import RecallTable from "./RecallTable.jsx";
import RecallUploadModal from "./RecallUploadModal.jsx";
import RecallDetailModal from "./RecallDetailModal.jsx";
import RecallOrderTab from "./RecallOrderTab.jsx";
import RecallDuplicateReview from "./RecallDuplicateReview.jsx";
import { isRecallBulkSelectable, nextRecallBulkStatus } from "./onlineDisplayUtils.js";
import "./online.css";

const EMPTY_SUMMARY = { total_count: 0, received_count: 0, remaining_count: 0, in_progress_count: 0, shipped_count: 0 };

export function RecallBulkBar({ selectedCount, nextStatus, disabled, isBulkUpdating, onChange }) {
  const actionLabel = nextStatus === "IN_PROGRESS" ? "진행중으로 변경" : nextStatus === "SHIPPED" ? "발송완료로 변경" : "다음 단계로 변경";
  return (
    <div className="online-recall-bulk-bar">
      <span>현재 페이지 선택 {selectedCount}건</span>
      {selectedCount > 0 && !nextStatus && <span className="online-recall-bulk-hint" role="status">같은 상태의 항목만 선택해야 합니다.</span>}
      <button type="button" className="primary-action" disabled={!nextStatus || disabled || isBulkUpdating} onClick={onChange}>
        {isBulkUpdating ? "처리 중..." : `${actionLabel} (${selectedCount})`}
      </button>
    </div>
  );
}

function RecallManagementPage({ currentUser }) {
  const [activeTab, setActiveTab] = useState("applications");
  const [uploadMode, setUploadMode] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [items, setItems] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isBulkUpdating, setIsBulkUpdating] = useState(false);
  const [bulkMessage, setBulkMessage] = useState("");
  const [bulkError, setBulkError] = useState("");
  const [filterValues, setFilterValues] = useState({ keyword: "", status: "" });
  const [appliedFilters, setAppliedFilters] = useState({ keyword: "", status: "" });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const loadData = useCallback(async (targetPage, filters, duplicateOnly) => {
    setIsLoading(true);
    setLoadError("");
    try {
      const [listResult, summaryResult] = await Promise.all([
        getRecallApplications({ ...filters, page: targetPage, page_size: 30, duplicate_only: duplicateOnly }),
        getRecallApplicationSummary(),
      ]);
      setItems(listResult.items || []);
      const selectableIds = new Set((listResult.items || []).filter((item) => isRecallBulkSelectable(item.current_status)).map((item) => item.id));
      setSelectedIds((current) => new Set([...current].filter((id) => selectableIds.has(id))));
      setTotal(listResult.total || 0);
      setTotalPages(listResult.total_pages || 1);
      setSummary(summaryResult || EMPTY_SUMMARY);
    } catch (caught) {
      setSelectedIds(new Set());
      setLoadError(caught?.message || "리콜 접수 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadData(page, appliedFilters, activeTab === "duplicates"); }, [loadData, page, appliedFilters, activeTab, refreshKey]);

  const handleSearch = () => {
    setSelectedIds(new Set());
    setBulkMessage("");
    setBulkError("");
    setPage(1);
    setAppliedFilters({ keyword: filterValues.keyword.trim(), status: filterValues.status });
  };

  const handleReset = () => {
    setSelectedIds(new Set());
    setBulkMessage("");
    setBulkError("");
    const cleared = { keyword: "", status: "" };
    setFilterValues(cleared);
    setPage(1);
    setAppliedFilters(cleared);
  };

  const handleRegistered = () => {
    setSelectedIds(new Set());
    setPage(1);
    setRefreshKey((value) => value + 1);
  };

  const handleToggleSelection = (id) => {
    if (!items.some((item) => item.id === id && isRecallBulkSelectable(item.current_status))) return;
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleTogglePage = (checked) => {
    setSelectedIds(new Set(checked ? items.filter((item) => isRecallBulkSelectable(item.current_status)).map((item) => item.id) : []));
  };

  const selectedStatuses = items.filter((item) => selectedIds.has(item.id)).map((item) => item.current_status);
  const nextStatus = nextRecallBulkStatus(selectedStatuses);

  const handleBulkChange = async () => {
    const ids = [...selectedIds];
    if (!ids.length || !nextStatus || isBulkUpdating) return;
    if (!window.confirm(`선택한 ${ids.length}건을 ${nextStatus === "IN_PROGRESS" ? "진행중" : "발송완료"}으로 변경하시겠습니까?`)) return;
    setIsBulkUpdating(true);
    setBulkError("");
    setBulkMessage("");
    try {
      const result = await bulkChangeRecallApplications(ids, nextStatus);
      setSelectedIds(new Set());
      setBulkMessage(`${nextStatus === "IN_PROGRESS" ? "진행중" : "발송완료"} 변경 완료: ${result.updated}건`);
      setRefreshKey((value) => value + 1);
    } catch (caught) {
      setBulkError(caught?.message || "일괄 상태 변경에 실패했습니다.");
    } finally {
      setIsBulkUpdating(false);
    }
  };

  const changePage = (nextPage) => {
    setSelectedIds(new Set());
    setBulkMessage("");
    setBulkError("");
    setPage(nextPage);
  };

  const changeTab = (tab) => {
    setSelectedIds(new Set());
    setPage(1);
    setFilterValues({ keyword: "", status: "" });
    setAppliedFilters({ keyword: "", status: "" });
    setActiveTab(tab);
  };

  return (
    <div className="online-page">
      <div className="portal-screen-heading online-recall-heading">
        <div>
          <h2>리콜 관리</h2>
          <p>리콜 대상 고객의 접수, 주문, 발송 진행 상태를 관리합니다.</p>
        </div>
        <div className="online-recall-actions">
          <button type="button" className="secondary-button" onClick={() => setUploadMode("application")}>접수 데이터 등록</button>
          <button type="button" className="primary-action" onClick={() => setUploadMode("target")}>리콜 대상 등록</button>
        </div>
      </div>
      <nav className="online-recall-tabs" aria-label="리콜 관리 탭">
        <button type="button" className={activeTab === "applications" ? "active" : ""} aria-current={activeTab === "applications" ? "page" : undefined} onClick={() => changeTab("applications")}>접수 목록</button>
        <button type="button" className={activeTab === "duplicates" ? "active" : ""} aria-current={activeTab === "duplicates" ? "page" : undefined} onClick={() => changeTab("duplicates")}>중복 확인</button>
        <button type="button" className={activeTab === "orders" ? "active" : ""} aria-current={activeTab === "orders" ? "page" : undefined} onClick={() => changeTab("orders")}>SCM 발주 대상</button>
      </nav>
      {activeTab === "orders" ? <RecallOrderTab isAdmin={currentUser?.role === "admin"} /> : <>
      <RecallSummaryCards summary={summary} />
      <section className="online-recall-list" aria-label="리콜 대상 목록">
        <RecallFilters
          values={filterValues}
          onChange={setFilterValues}
          onSearch={handleSearch}
          onReset={handleReset}
          isLoading={isLoading || isBulkUpdating}
        />
        {activeTab === "applications" && <RecallBulkBar selectedCount={selectedIds.size} nextStatus={nextStatus} disabled={isLoading || Boolean(loadError)} isBulkUpdating={isBulkUpdating} onChange={handleBulkChange} />}
        {bulkMessage && <p className="online-recall-bulk-message" role="status">{bulkMessage}</p>}
        {bulkError && <p className="online-recall-bulk-error" role="alert">{bulkError}</p>}
        {activeTab === "duplicates" ? <RecallDuplicateReview items={items} isLoading={isLoading} error={loadError} onDetail={setDetailId} onResolved={() => { setPage(1); setRefreshKey((value) => value + 1); }} /> : <RecallTable items={items} isLoading={isLoading} isBulkUpdating={isBulkUpdating} error={loadError} selectedIds={selectedIds} onToggleSelection={handleToggleSelection} onTogglePage={handleTogglePage} onOpenDetail={setDetailId} />}
        <div className="online-recall-pagination">
          <span>총 {total}건 · {page}/{totalPages} 페이지</span>
          <div>
            <button type="button" className="secondary-button" disabled={page <= 1 || isLoading || isBulkUpdating} onClick={() => changePage(page - 1)}>이전</button>
            <button type="button" className="secondary-button" disabled={page >= totalPages || isLoading || isBulkUpdating} onClick={() => changePage(page + 1)}>다음</button>
          </div>
        </div>
      </section>
      </>}
      {uploadMode && <RecallUploadModal mode={uploadMode} onClose={() => setUploadMode(null)} onRegistered={handleRegistered} />}
      {detailId !== null && <RecallDetailModal applicationId={detailId} onClose={() => setDetailId(null)} onChanged={() => { setSelectedIds(new Set()); setRefreshKey((value) => value + 1); }} />}
    </div>
  );
}

export default RecallManagementPage;
