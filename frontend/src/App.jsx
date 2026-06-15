import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createAsset,
  downloadAssetsExcel,
  getAssets,
  getCategories,
  getDatabaseHealth,
  getDepartments,
  getHealth,
  getStatsByCategory,
  getStatsByDepartment,
  getStatsMonthly,
  getStatsSummary,
} from "./api/client.js";
import AssetDetail from "./components/AssetDetail.jsx";
import AssetForm from "./components/AssetForm.jsx";
import AssetList from "./components/AssetList.jsx";
import CategoryStats from "./components/CategoryStats.jsx";
import DepartmentStats from "./components/DepartmentStats.jsx";
import AssetExcelTools from "./components/AssetExcelTools.jsx";
import FilterBar from "./components/FilterBar.jsx";
import MonthlyStats from "./components/MonthlyStats.jsx";
import PortalHero from "./components/PortalHero.jsx";
import PortalSidebar from "./components/PortalSidebar.jsx";
import QuickAssetForm from "./components/QuickAssetForm.jsx";
import RecentActivityPanel from "./components/RecentActivityPanel.jsx";
import ShortcutPanel from "./components/ShortcutPanel.jsx";
import StatsSummary from "./components/StatsSummary.jsx";
import "./styles/app.css";

const INITIAL_FILTERS = {
  keyword: "",
  status: "",
  category_id: "",
  department_id: "",
};

const INITIAL_SORT = {
  key: "",
  direction: "asc",
};

const INITIAL_STATS_SUMMARY = {
  total_assets: 0,
  in_use_assets: 0,
  unused_assets: 0,
  disposed_assets: 0,
  total_purchase_amount: 0,
};

function App() {
  const [backendStatus, setBackendStatus] = useState({
    isLoading: false,
    message: "백엔드 연결 상태를 확인할 수 있습니다.",
    type: "idle",
  });
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [assets, setAssets] = useState([]);
  const [statsSummary, setStatsSummary] = useState(INITIAL_STATS_SUMMARY);
  const [statsState, setStatsState] = useState({ isLoading: false, error: "" });
  const [categoryStats, setCategoryStats] = useState([]);
  const [categoryStatsState, setCategoryStatsState] = useState({
    isLoading: false,
    error: "",
  });
  const [departmentStats, setDepartmentStats] = useState([]);
  const [departmentStatsState, setDepartmentStatsState] = useState({
    isLoading: false,
    error: "",
  });
  const [monthlyStats, setMonthlyStats] = useState([]);
  const [monthlyStatsState, setMonthlyStatsState] = useState({
    isLoading: false,
    error: "",
  });
  const [categories, setCategories] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [assetState, setAssetState] = useState({ isLoading: false, error: "" });
  const [exportState, setExportState] = useState({ isLoading: false, error: "" });
  const [lookupState, setLookupState] = useState({
    isLoading: false,
    categoryError: "",
    departmentError: "",
  });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [sortConfig, setSortConfig] = useState(INITIAL_SORT);
  const [activeSection, setActiveSection] = useState("dashboard");

  const activeFilters = useMemo(
    () => ({
      keyword: filters.keyword.trim(),
      status: filters.status,
      category_id: filters.category_id,
      department_id: filters.department_id,
    }),
    [filters],
  );

  const hasActiveFilters = useMemo(
    () => Object.values(activeFilters).some((value) => value !== ""),
    [activeFilters],
  );

  const displayedAssets = useMemo(
    () => sortAssets(assets, sortConfig),
    [assets, sortConfig],
  );

  const sortLabel = useMemo(() => getSortLabel(sortConfig), [sortConfig]);

  const checkBackend = useCallback(async () => {
    setBackendStatus({
      isLoading: true,
      message: "백엔드 상태를 확인 중입니다.",
      type: "idle",
    });

    try {
      const [healthResult, dbResult] = await Promise.allSettled([
        getHealth(),
        getDatabaseHealth(),
      ]);

      if (healthResult.status === "rejected") {
        throw healthResult.reason;
      }

      const dbHealth =
        dbResult.status === "fulfilled" ? dbResult.value : { status: "error" };
      const dbMessage = dbHealth.status === "ok" ? "DB 연결 정상" : "DB 연결 확인 필요";
      setBackendStatus({
        isLoading: false,
        message: `${healthResult.value.service || "Backend"} 정상, ${dbMessage}`,
        type: dbHealth.status === "ok" ? "ok" : "warning",
      });
    } catch (error) {
      setBackendStatus({
        isLoading: false,
        message: error.message,
        type: "error",
      });
    } finally {
      setBackendStatus((current) => ({
        ...current,
        isLoading: false,
      }));
    }
  }, []);

  const loadLookups = useCallback(async () => {
    setLookupState({ isLoading: true, categoryError: "", departmentError: "" });
    try {
      const [categoryResult, departmentResult] = await Promise.allSettled([
        getCategories(),
        getDepartments(),
      ]);

      const categoryData =
        categoryResult.status === "fulfilled"
          ? categoryResult.value
          : [];
      const departmentData =
        departmentResult.status === "fulfilled"
          ? departmentResult.value
          : [];

      setCategories(categoryData);
      setDepartments(departmentData);
      setLookupState({
        isLoading: false,
        categoryError:
          categoryResult.status === "rejected" ? categoryResult.reason.message : "",
        departmentError:
          departmentResult.status === "rejected" ? departmentResult.reason.message : "",
      });
    } catch (error) {
      setCategories([]);
      setDepartments([]);
      setLookupState({
        isLoading: false,
        categoryError: error.message,
        departmentError: error.message,
      });
    }
  }, []);

  const loadAssets = useCallback(async () => {
    setAssetState({ isLoading: true, error: "" });
    try {
      const data = await getAssets(activeFilters);
      const nextAssets = Array.isArray(data) ? data : [];
      setAssets(nextAssets);
      setSelectedAssetId((currentId) => {
        if (!currentId || nextAssets.some((asset) => asset.id === currentId)) {
          return currentId;
        }
        return null;
      });
      setAssetState({ isLoading: false, error: "" });
    } catch (error) {
      setAssets([]);
      setSelectedAssetId(null);
      setAssetState({ isLoading: false, error: error.message });
    } finally {
      setAssetState((current) => ({
        ...current,
        isLoading: false,
      }));
    }
  }, [activeFilters]);

  const loadStats = useCallback(async () => {
    setStatsState({ isLoading: true, error: "" });
    setCategoryStatsState({ isLoading: true, error: "" });
    setDepartmentStatsState({ isLoading: true, error: "" });
    setMonthlyStatsState({ isLoading: true, error: "" });

    const [summaryResult, categoryResult, departmentResult, monthlyResult] =
      await Promise.allSettled([
        getStatsSummary(),
        getStatsByCategory(),
        getStatsByDepartment(),
        getStatsMonthly(),
      ]);

    if (summaryResult.status === "fulfilled") {
      setStatsSummary({ ...INITIAL_STATS_SUMMARY, ...(summaryResult.value || {}) });
      setStatsState({ isLoading: false, error: "" });
    } else {
      setStatsSummary(INITIAL_STATS_SUMMARY);
      setStatsState({ isLoading: false, error: summaryResult.reason.message });
    }

    if (categoryResult.status === "fulfilled") {
      setCategoryStats(Array.isArray(categoryResult.value) ? categoryResult.value : []);
      setCategoryStatsState({ isLoading: false, error: "" });
    } else {
      setCategoryStats([]);
      setCategoryStatsState({
        isLoading: false,
        error: categoryResult.reason.message,
      });
    }

    if (departmentResult.status === "fulfilled") {
      setDepartmentStats(
        Array.isArray(departmentResult.value) ? departmentResult.value : [],
      );
      setDepartmentStatsState({ isLoading: false, error: "" });
    } else {
      setDepartmentStats([]);
      setDepartmentStatsState({
        isLoading: false,
        error: departmentResult.reason.message,
      });
    }

    if (monthlyResult.status === "fulfilled") {
      setMonthlyStats(Array.isArray(monthlyResult.value) ? monthlyResult.value : []);
      setMonthlyStatsState({ isLoading: false, error: "" });
    } else {
      setMonthlyStats([]);
      setMonthlyStatsState({
        isLoading: false,
        error: monthlyResult.reason.message,
      });
    }
  }, []);

  useEffect(() => {
    checkBackend();
    loadLookups();
  }, [checkBackend, loadLookups]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const handleCreateAsset = async (payload) => {
    setIsSubmitting(true);
    setFormError("");

    try {
      await createAsset(payload);
      setIsFormOpen(false);
      await Promise.all([loadAssets(), loadStats()]);
      return true;
    } catch (error) {
      setFormError(error.message);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickCreateAsset = async (payload) => {
    await createAsset(payload);
    await Promise.all([loadAssets(), loadStats()]);
  };

  const handleAssetUpdated = async (assetId) => {
    await Promise.all([loadAssets(), loadStats()]);
    setSelectedAssetId(assetId);
  };

  const handleAssetDeleted = async () => {
    setSelectedAssetId(null);
    await Promise.all([loadAssets(), loadStats()]);
  };

  const handleResetFilters = () => {
    setFilters(INITIAL_FILTERS);
  };

  const handleSortChange = (key) => {
    setSortConfig((current) => {
      if (current.key !== key) {
        return { key, direction: "asc" };
      }

      if (current.direction === "asc") {
        return { key, direction: "desc" };
      }

      return INITIAL_SORT;
    });
  };

  const handleExportExcel = async () => {
    setExportState({ isLoading: true, error: "" });
    try {
      const { blob, filename } = await downloadAssetsExcel(activeFilters);
      downloadBlob(blob, filename || getFallbackExcelFilename());
      setExportState({ isLoading: false, error: "" });
    } catch (error) {
      setExportState({ isLoading: false, error: error.message });
    }
  };

  const handleNavigate = (sectionId) => {
    const sectionMap = {
      quick: "assets",
      reports: "stats",
      activity: "history",
    };
    const nextSection = sectionMap[sectionId] || sectionId;
    setActiveSection(nextSection);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const renderStatsReports = (className = "portal-report-grid") => (
    <section className={className}>
      <CategoryStats
        items={categoryStats}
        isLoading={categoryStatsState.isLoading}
        error={categoryStatsState.error}
      />

      <DepartmentStats
        items={departmentStats}
        isLoading={departmentStatsState.isLoading}
        error={departmentStatsState.error}
      />

      <MonthlyStats
        items={monthlyStats}
        isLoading={monthlyStatsState.isLoading}
        error={monthlyStatsState.error}
      />
    </section>
  );

  const renderAssetManagement = () => (
    <section className="content-panel portal-assets-panel">
      <div className="section-heading">
        <div>
          <h2>자산 관리</h2>
          <p>빠른 등록과 검색/필터로 등록 자산을 관리합니다.</p>
        </div>
        {(lookupState.categoryError || lookupState.departmentError) && (
          <span className="lookup-warning">
            분류/부서 선택값을 불러오지 못했습니다.
          </span>
        )}
      </div>

      <QuickAssetForm
        categories={categories}
        departments={departments}
        isCategoryDisabled={
          lookupState.isLoading ||
          Boolean(lookupState.categoryError) ||
          categories.length === 0
        }
        onSubmit={handleQuickCreateAsset}
        onOpenDetailedCreate={() => {
          setFormError("");
          setIsFormOpen(true);
        }}
      />

      <FilterBar
        filters={filters}
        categories={categories}
        departments={departments}
        isLookupDisabled={Boolean(
          lookupState.categoryError && lookupState.departmentError,
        )}
        onFilterChange={setFilters}
        onRefresh={() => {
          loadLookups();
          loadAssets();
          loadStats();
        }}
        onReset={handleResetFilters}
        onOpenCreate={() => {
          setFormError("");
          setIsFormOpen(true);
        }}
        isLoading={assetState.isLoading}
        hasActiveFilters={hasActiveFilters}
        sortLabel={sortLabel}
      />

      <AssetList
        assets={displayedAssets}
        isLoading={assetState.isLoading}
        error={assetState.error}
        hasActiveFilters={hasActiveFilters}
        selectedAssetId={selectedAssetId}
        onSelectAsset={setSelectedAssetId}
        sortConfig={sortConfig}
        onSortChange={handleSortChange}
      />
    </section>
  );

  const renderExcelManagement = () => (
    <section className="content-panel portal-excel-panel">
      <div className="section-heading">
        <div>
          <h2>엑셀 관리</h2>
          <p>
            엑셀 양식을 내려받아 작성한 뒤 업로드하여 여러 자산을 한 번에 등록할 수
            있습니다.
          </p>
        </div>
      </div>

      <AssetExcelTools
        onImportCommitted={() => Promise.all([loadLookups(), loadAssets(), loadStats()])}
        onExportExcel={handleExportExcel}
        isExporting={exportState.isLoading}
        exportError={exportState.error}
      />
    </section>
  );

  const renderReadyCard = (title, description) => (
    <section className="settings-placeholder portal-ready-card">
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );

  const renderActiveSection = () => {
    if (activeSection === "assets") {
      return renderAssetManagement();
    }

    if (activeSection === "excel") {
      return renderExcelManagement();
    }

    if (activeSection === "stats") {
      return (
        <>
          <div className="portal-screen-heading">
            <h2>통계 / 리포트</h2>
            <p>자산 현황과 분류, 부서, 월별 흐름을 확인합니다.</p>
          </div>
          <StatsSummary
            summary={statsSummary}
            isLoading={statsState.isLoading}
            error={statsState.error}
          />
          {renderStatsReports()}
        </>
      );
    }

    if (activeSection === "history") {
      return renderReadyCard(
        "변경 이력",
        "전체 변경 이력 화면은 준비 중입니다. 현재는 자산 상세 모달에서 개별 이력을 확인할 수 있습니다.",
      );
    }

    if (activeSection === "settings") {
      return renderReadyCard(
        "설정",
        "조직별 운영 정책과 권한 설정은 다음 단계에서 확장할 수 있습니다.",
      );
    }

    return (
      <>
        <PortalHero onNavigate={handleNavigate} />
        <StatsSummary
          summary={statsSummary}
          isLoading={statsState.isLoading}
          error={statsState.error}
        />
        {renderStatsReports("portal-report-grid portal-dashboard-reports")}
      </>
    );
  };

  return (
    <div className="portal-shell">
      <PortalSidebar activeSection={activeSection} onNavigate={handleNavigate} />

      <div className="portal-workspace">
        <header className="portal-topbar">
          <button
            type="button"
            className="icon-button portal-menu-button"
            aria-label="메뉴"
          >
            ☰
          </button>
          <label className="portal-search" aria-label="통합 검색">
            <span aria-hidden="true">⌕</span>
            <input
              value={filters.keyword}
              onChange={(event) => setFilters({ ...filters, keyword: event.target.value })}
              placeholder="자산 검색 (제품명, 시리얼번호, 모델명)"
            />
          </label>
          <div className="portal-topbar-actions">
            <span className={`status-chip status-chip-${backendStatus.type}`}>
              {formatBackendStatus(backendStatus)}
            </span>
            <button
              type="button"
              className="secondary-button compact-button"
              onClick={checkBackend}
              disabled={backendStatus.isLoading}
            >
              {backendStatus.isLoading ? "확인 중" : "상태 확인"}
            </button>
            <button type="button" className="icon-button portal-alert-button" aria-label="알림">
              ◦
            </button>
            <div className="portal-user">
              <strong>관리자</strong>
              <span>Asset Admin</span>
            </div>
          </div>
        </header>

        <div
          className={
            activeSection === "excel"
              ? "portal-content portal-content-wide"
              : "portal-content"
          }
        >
          <main className="portal-main">{renderActiveSection()}</main>

          {activeSection !== "excel" && (
            <aside className="portal-aside">
              <ShortcutPanel onNavigate={handleNavigate} />
              <RecentActivityPanel assets={displayedAssets} onNavigate={handleNavigate} />
            </aside>
          )}
        </div>
      </div>

      {selectedAssetId && (
        <AssetDetail
          assetId={selectedAssetId}
          categories={categories}
          departments={departments}
          lookupError={lookupState.categoryError || lookupState.departmentError}
          onClose={() => setSelectedAssetId(null)}
          onAssetUpdated={handleAssetUpdated}
          onAssetDeleted={handleAssetDeleted}
        />
      )}

      <AssetForm
        categories={categories}
        departments={departments}
        lookupState={lookupState}
        isOpen={isFormOpen}
        isSubmitting={isSubmitting}
        error={formError}
        onClose={() => setIsFormOpen(false)}
        onSubmit={handleCreateAsset}
      />
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

function getFallbackExcelFilename() {
  const today = new Date().toISOString().slice(0, 10);
  return `asset_list_${today}.xlsx`;
}

function sortAssets(items, sortConfig) {
  if (!sortConfig.key) {
    return Array.isArray(items) ? items : [];
  }

  return [...items].sort((left, right) => {
    const leftValue = normalizeSortValue(getSortValue(left, sortConfig.key));
    const rightValue = normalizeSortValue(getSortValue(right, sortConfig.key));
    const result = leftValue.localeCompare(rightValue, "ko-KR", {
      numeric: true,
      sensitivity: "base",
    });
    return sortConfig.direction === "asc" ? result : -result;
  });
}

function getSortValue(asset, key) {
  if (key === "department_name") {
    return asset?.department_name || asset?.user_name;
  }
  return asset?.[key];
}

function normalizeSortValue(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function getSortLabel(sortConfig) {
  const labelMap = {
    name: "제품명",
    status: "상태",
    department_name: "부서(사용자명)",
    serial_number: "시리얼번호",
  };

  if (!sortConfig.key) {
    return "현재 정렬: 최신 등록순";
  }

  const direction = sortConfig.direction === "desc" ? "내림차순" : "오름차순";
  return `현재 정렬: ${labelMap[sortConfig.key]} ${direction}`;
}

function formatBackendStatus(status) {
  if (status.isLoading) {
    return "상태 확인 중";
  }
  if (status.type === "ok") {
    return "Backend 정상 · DB 정상";
  }
  if (status.type === "idle") {
    return "상태 확인 대기";
  }
  return "연결 확인 필요";
}

export default App;
