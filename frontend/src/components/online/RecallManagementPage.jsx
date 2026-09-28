import React, { useCallback, useEffect, useState } from "react";
import { getRecallApplications, getRecallApplicationSummary } from "../../api/client.js";
import RecallFilters from "./RecallFilters.jsx";
import RecallSummaryCards from "./RecallSummaryCards.jsx";
import RecallTable from "./RecallTable.jsx";
import RecallUploadModal from "./RecallUploadModal.jsx";
import RecallDetailModal from "./RecallDetailModal.jsx";
import "./online.css";

const EMPTY_SUMMARY = { total: 0, received: 0, orders: 0, shipped: 0 };

function RecallManagementPage() {
  const [uploadMode, setUploadMode] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [items, setItems] = useState([]);
  const [filterValues, setFilterValues] = useState({ keyword: "", status: "" });
  const [appliedFilters, setAppliedFilters] = useState({ keyword: "", status: "" });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const loadData = useCallback(async (targetPage, filters) => {
    setIsLoading(true);
    setLoadError("");
    try {
      const [listResult, summaryResult] = await Promise.all([
        getRecallApplications({ ...filters, page: targetPage, page_size: 30 }),
        getRecallApplicationSummary(),
      ]);
      setItems(listResult.items || []);
      setTotal(listResult.total || 0);
      setTotalPages(listResult.total_pages || 1);
      setSummary(summaryResult || EMPTY_SUMMARY);
    } catch (caught) {
      setLoadError(caught?.message || "리콜 접수 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadData(page, appliedFilters); }, [loadData, page, appliedFilters, refreshKey]);

  const handleSearch = () => {
    setPage(1);
    setAppliedFilters({ keyword: filterValues.keyword.trim(), status: filterValues.status });
  };

  const handleReset = () => {
    const cleared = { keyword: "", status: "" };
    setFilterValues(cleared);
    setPage(1);
    setAppliedFilters(cleared);
  };

  const handleRegistered = () => {
    setPage(1);
    setRefreshKey((value) => value + 1);
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
      <RecallSummaryCards summary={summary} />
      <section className="online-recall-list" aria-label="리콜 대상 목록">
        <RecallFilters
          values={filterValues}
          onChange={setFilterValues}
          onSearch={handleSearch}
          onReset={handleReset}
          isLoading={isLoading}
        />
        <RecallTable items={items} isLoading={isLoading} error={loadError} onOpenDetail={setDetailId} />
        <div className="online-recall-pagination">
          <span>총 {total}건 · {page}/{totalPages} 페이지</span>
          <div>
            <button type="button" className="secondary-button" disabled={page <= 1 || isLoading} onClick={() => setPage((value) => value - 1)}>이전</button>
            <button type="button" className="secondary-button" disabled={page >= totalPages || isLoading} onClick={() => setPage((value) => value + 1)}>다음</button>
          </div>
        </div>
      </section>
      {uploadMode && <RecallUploadModal mode={uploadMode} onClose={() => setUploadMode(null)} onRegistered={handleRegistered} />}
      {detailId !== null && <RecallDetailModal applicationId={detailId} onClose={() => setDetailId(null)} onChanged={() => setRefreshKey((value) => value + 1)} />}
    </div>
  );
}

export default RecallManagementPage;
