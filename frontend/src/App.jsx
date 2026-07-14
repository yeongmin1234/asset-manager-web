import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createCategory,
  createAsset,
  downloadAssetsExcel,
  getAdminStatus,
  getAssets,
  getCategories,
  getDatabaseHealth,
  getDepartments,
  getExpirationScheduleSummary,
  getHealth,
  getMenuVisibility,
  getRecentActivityLogs,
  getStatsByCategory,
  getStatsByDepartment,
  getStatsMonthly,
  getStatsSummary,
  getVisitorsSummary,
  pingVisitor,
  resetAdminPassword,
  updateAdminPassword,
  updateMenuVisibility,
  verifyAdminPassword,
} from "./api/client.js";
import AdminAuthModal from "./components/AdminAuthModal.jsx";
import AdminPasswordResetModal from "./components/AdminPasswordResetModal.jsx";
import AssetDetail from "./components/AssetDetail.jsx";
import AssetForm from "./components/AssetForm.jsx";
import AssetList from "./components/AssetList.jsx";
import CategoryCreateModal from "./components/CategoryCreateModal.jsx";
import CategoryStats from "./components/CategoryStats.jsx";
import BeverageOrderPage from "./components/BeverageOrderPage.jsx";
import DashboardPage from "./components/DashboardPage.jsx";
import DepartmentStats from "./components/DepartmentStats.jsx";
import ExpirationSchedulePage, { formatDaysLeft, getCategoryLabel, openExpirationScheduleFilter } from "./components/ExpirationSchedulePage.jsx";
import AssetExcelTools from "./components/AssetExcelTools.jsx";
import FilterBar from "./components/FilterBar.jsx";
import HistoryPage from "./components/HistoryPage.jsx";
import HrAccountListPage from "./components/HrAccountListPage.jsx";
import InstallLibraryPage from "./components/InstallLibraryPage.jsx";
import MonthlyStats from "./components/MonthlyStats.jsx";
import NetworkStatusPage from "./components/NetworkStatusPage.jsx";
import PajuFireInsurancePage from "./components/PajuFireInsurancePage.jsx";
import PortalSidebar, { MENU_ITEMS } from "./components/PortalSidebar.jsx";
import QuickAssetForm from "./components/QuickAssetForm.jsx";
import RecentActivityPanel from "./components/RecentActivityPanel.jsx";
import ScmPage from "./components/ScmPage.jsx";
import ServerStatusPopover from "./components/ServerStatusPopover.jsx";
import SettingsPage from "./components/SettingsPage.jsx";
import SoftwarePage from "./components/SoftwarePage.jsx";
import StatsSummary from "./components/StatsSummary.jsx";
import VehiclePage from "./components/VehiclePage.jsx";
import VendorContactsPage from "./components/VendorContactsPage.jsx";
import WorkManualPage from "./components/WorkManualPage.jsx";
import UserManagementPage from "./components/UserManagementPage.jsx";
import {
  ASSET_SORT_OPTIONS,
  SORT_VALUES,
  SortSelect,
  sortItems,
} from "./utils/sortOptions.jsx";
import { getAllowedSectionIds } from "./utils/menuPermissions.js";
import useMenuAccessLog from "./hooks/useMenuAccessLog.js";
import "./styles/app.css";

const INITIAL_FILTERS = {
  keyword: "",
  status: "",
  category_id: "",
  location_group: "",
  department_id: "",
};

const INITIAL_STATS_SUMMARY = {
  total_assets: 0,
  in_use_assets: 0,
  unused_assets: 0,
  disposed_assets: 0,
  total_purchase_amount: 0,
};

const SIDEBAR_COLLAPSED_STORAGE_KEY = "assetManager.sidebarCollapsed";
const PROTECTED_MENU_STORAGE_KEY = "assetManager.protectedMenus";
const ADMIN_AUTH_STORAGE_KEY = "assetManager.adminAuth";
const DEFAULT_MENU_VISIBILITY = {
  dashboard: true,
  drink_orders: true,
  work_manual: true,
  vendor_contacts: true,
  expiration_schedules: true,
  assets: true,
  software: true,
  company_cars: true,
  fire_insurance: true,
  network: true,
  excel_management: true,
  statistics: true,
  history: true,
  install_files: true,
  hr_list: true,
  scm: true,
  user_management: true,
  settings: true,
};
const SECTION_MENU_KEYS = Object.fromEntries(MENU_ITEMS.map((item) => [item.id, item.menuKey]));
const DEFAULT_PROTECTED_MENUS = {
  software: false,
  vehicles: false,
  "paju-fire-insurance": false,
  "beverage-orders": false,
  "work-manuals": false,
  expiration_schedules: false,
  network: false,
  history: false,
  "install-library": false,
  "hr-list": false,
  scm: true,
  settings: false,
};
const MENU_LABELS = {
  dashboard: "대시보드",
  assets: "자산 관리",
  software: "SW 현황",
  vehicles: "법인차량 관리",
  "paju-fire-insurance": "파주화재보험",
  "beverage-orders": "음료주문기록",
  "work-manuals": "업무설명서",
  "vendor-contacts": "업체연락처",
  expiration_schedules: "점검·만료 관리",
  network: "네트워크 현황",
  excel: "엑셀 관리",
  stats: "통계 / 리포트",
  history: "변경 이력",
  "install-library": "설치자료실",
  "hr-list": "인사업무 리스트",
  scm: "SCM",
  users: "사용자 관리",
  settings: "설정",
};
function App({ currentUser, onLogout }) {
  const isAdmin = currentUser?.role === "admin";
  const allowedSections = useMemo(
    () => new Set(getAllowedSectionIds(currentUser?.menu_permissions || [])),
    [currentUser?.menu_permissions],
  );
  const [backendStatus, setBackendStatus] = useState({
    backendOk: null,
    checkedAt: null,
    dbOk: null,
    isLoading: false,
    message: "백엔드 연결 상태를 확인할 수 있습니다.",
    type: "idle",
  });
  const [visitorSummary, setVisitorSummary] = useState({
    active_count: null,
    active_window_seconds: 180,
    visitors: [],
    error: "",
  });
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "true";
  });
  const [menuVisibility, setMenuVisibility] = useState(DEFAULT_MENU_VISIBILITY);
  const [menuVisibilityError, setMenuVisibilityError] = useState("");
  const [protectedMenus, setProtectedMenus] = useState(() => getStoredProtectedMenus());
  const [adminStatus, setAdminStatus] = useState({
    configured: false,
    error: "",
    isLoading: true,
  });
  const [adminAuthModal, setAdminAuthModal] = useState({
    error: "",
    isOpen: false,
    isSubmitting: false,
    targetSection: "",
  });
  const [adminAuthClearedAt, setAdminAuthClearedAt] = useState(null);
  const [adminResetModal, setAdminResetModal] = useState({
    error: "",
    isOpen: false,
    isSubmitting: false,
  });
  const [adminResetSuccessMessage, setAdminResetSuccessMessage] = useState("");
  const [isServerStatusOpen, setIsServerStatusOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [notificationLogs, setNotificationLogs] = useState([]);
  const [notificationState, setNotificationState] = useState({ error: "", isLoading: false });
  const notificationRef = useRef(null);
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
  const [categoryCreateState, setCategoryCreateState] = useState({
    isOpen: false,
    isSubmitting: false,
    error: "",
  });
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [sortValue, setSortValue] = useState(SORT_VALUES.latest);
  const [activeSection, setActiveSection] = useState(() =>
    typeof window !== "undefined" && window.location.pathname === "/hr/list" ? "hr-list" : "dashboard",
  );
  const [accessDeniedSection, setAccessDeniedSection] = useState("");
  useMenuAccessLog(activeSection, Boolean(currentUser) && menuVisibility[SECTION_MENU_KEYS[activeSection]] !== false && !accessDeniedSection && (isAdmin || allowedSections.has(activeSection)));
  useEffect(() => {
    let active = true;
    getMenuVisibility()
      .then((response) => {
        if (active) setMenuVisibility({ ...DEFAULT_MENU_VISIBILITY, ...(response?.visibility || {}) });
      })
      .catch(() => { if (active) setMenuVisibilityError("메뉴 표시 설정을 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [currentUser?.id]);

  const activeFilters = useMemo(
    () => ({
      keyword: filters.keyword.trim(),
      status: filters.status,
      category_id: filters.category_id,
      location_group: filters.location_group,
      department_id: filters.department_id,
    }),
    [filters],
  );

  const hasActiveFilters = useMemo(
    () => Object.values(activeFilters).some((value) => value !== ""),
    [activeFilters],
  );

  const displayedAssets = useMemo(
    () => sortItems(assets, sortValue, {
      created: ["created_at", "registered_at", "purchase_date"],
      updated: ["updated_at", "created_at"],
      name: ["name", "asset_name"],
    }),
    [assets, sortValue],
  );

  const loadAdminStatus = useCallback(async () => {
    try {
      const status = await getAdminStatus();
      setAdminStatus({
        configured: status?.configured === true,
        error: "",
        isLoading: false,
      });
    } catch (error) {
      setAdminStatus({
        configured: false,
        error: error.message,
        isLoading: false,
      });
    }
  }, []);

  const checkBackend = useCallback(async () => {
    setBackendStatus((current) => ({
      ...current,
      isLoading: true,
      message: "백엔드 상태를 확인 중입니다.",
      type: "idle",
    }));

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
        backendOk: true,
        checkedAt: new Date().toISOString(),
        dbOk: dbHealth.status === "ok",
        isLoading: false,
        message: `${healthResult.value.service || "Backend"} 정상, ${dbMessage}`,
        type: dbHealth.status === "ok" ? "ok" : "warning",
      });
    } catch (error) {
      setBackendStatus({
        backendOk: false,
        checkedAt: new Date().toISOString(),
        dbOk: false,
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

  const refreshVisitors = useCallback(async () => {
    try {
      await pingVisitor();
      const summary = await getVisitorsSummary();
      setVisitorSummary({
        active_count: Number(summary?.active_count || 0),
        active_window_seconds: Number(summary?.active_window_seconds || 180),
        visitors: Array.isArray(summary?.visitors) ? summary.visitors : [],
        error: "",
      });
    } catch (error) {
      setVisitorSummary((current) => ({
        ...current,
        error: error.message,
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
    loadAdminStatus();
    loadLookups();
    refreshVisitors();
  }, [checkBackend, loadAdminStatus, loadLookups, refreshVisitors]);

  useEffect(() => {
    const intervalId = window.setInterval(refreshVisitors, 30000);
    return () => window.clearInterval(intervalId);
  }, [refreshVisitors]);

  const loadNotificationLogs = useCallback(async () => {
    setNotificationState({ error: "", isLoading: true });
    const [activityResult, expirationResult] = await Promise.allSettled([
      getRecentActivityLogs(8),
      getExpirationScheduleSummary(),
    ]);
    const activityLogs =
      activityResult.status === "fulfilled" && Array.isArray(activityResult.value)
        ? activityResult.value
        : [];
    const expirationItems =
      expirationResult.status === "fulfilled"
        ? buildExpirationNotificationItems(expirationResult.value?.upcoming_items)
        : [];
    setNotificationLogs([...expirationItems, ...activityLogs].slice(0, 8));
    setNotificationState({
      error:
        activityResult.status === "rejected" && expirationResult.status === "rejected"
          ? activityResult.reason.message
          : "",
      isLoading: false,
    });
  }, []);

  useEffect(() => {
    if (isNotificationOpen) {
      loadNotificationLogs();
    }
  }, [isNotificationOpen, loadNotificationLogs]);

  useEffect(() => {
    if (!isNotificationOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (!notificationRef.current?.contains(event.target)) {
        setIsNotificationOpen(false);
      }
    };
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsNotificationOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isNotificationOpen]);

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

  const handleCategoryTabSelect = (categoryId) => {
    setFilters((current) => ({
      ...current,
      category_id: categoryId,
    }));
  };

  const handleLocationTabSelect = (locationGroup) => {
    setFilters((current) => ({
      ...current,
      location_group: locationGroup,
    }));
  };

  const handleCreateCategory = async (name) => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      setCategoryCreateState((current) => ({
        ...current,
        error: "분류명을 입력해주세요.",
      }));
      return false;
    }

    const hasDuplicate = categories.some(
      (category) => category.name.trim().toLowerCase() === trimmedName.toLowerCase(),
    );
    if (hasDuplicate) {
      setCategoryCreateState((current) => ({
        ...current,
        error: "이미 존재하는 분류명입니다.",
      }));
      return false;
    }

    setCategoryCreateState((current) => ({
      ...current,
      isSubmitting: true,
      error: "",
    }));

    try {
      const created = await createCategory({ name: trimmedName });
      setCategories((current) => [...current, created]);
      setFilters((current) => ({
        ...current,
        category_id: String(created.id),
      }));
      setCategoryCreateState({ isOpen: false, isSubmitting: false, error: "" });
      await loadLookups();
      return true;
    } catch (error) {
      setCategoryCreateState((current) => ({
        ...current,
        isSubmitting: false,
        error: error.message,
      }));
      return false;
    }
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
    if (!isAdmin && !allowedSections.has(nextSection)) {
      setAccessDeniedSection(nextSection);
      setActiveSection(nextSection);
      return;
    }
    setAccessDeniedSection("");
    if (adminStatus.configured && protectedMenus[nextSection] && !hasValidAdminAuth()) {
      setAdminAuthModal({
        error: "",
        isOpen: true,
        isSubmitting: false,
        targetSection: nextSection,
      });
      return;
    }

    navigateToSection(nextSection);
  };

  const navigateToSection = (nextSection) => {
    setActiveSection(nextSection);
    if (typeof window !== "undefined") {
      const nextPath = nextSection === "hr-list" ? "/hr/list" : "/";
      if (window.location.pathname !== nextPath) window.history.pushState({}, "", nextPath);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handlePortalSearchKeyDown = (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    const keyword = filters.keyword.trim();
    if (!keyword) {
      return;
    }
    navigateToSection("assets");
  };

  const handleProtectedMenuChange = (menuId, isProtected) => {
    const nextProtectedMenus = {
      ...DEFAULT_PROTECTED_MENUS,
      ...protectedMenus,
      [menuId]: isProtected,
    };

    setProtectedMenus(nextProtectedMenus);

    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        PROTECTED_MENU_STORAGE_KEY,
        JSON.stringify(nextProtectedMenus),
      );
    }
  };

  const handleAdminAuthSubmit = async (password) => {
    setAdminAuthModal((current) => ({
      ...current,
      error: "",
      isSubmitting: true,
    }));

    try {
      const result = await verifyAdminPassword(password);
      saveAdminAuth(result);
      const targetSection = adminAuthModal.targetSection;
      setAdminAuthModal({
        error: "",
        isOpen: false,
        isSubmitting: false,
        targetSection: "",
      });
      navigateToSection(targetSection);
    } catch (error) {
      setAdminAuthModal((current) => ({
        ...current,
        error: error.message,
        isSubmitting: false,
      }));
    }
  };

  const handleAdminAuthCancel = () => {
    setAdminAuthModal({
      error: "",
      isOpen: false,
      isSubmitting: false,
      targetSection: "",
    });
  };

  const handleAdminPasswordResetOpen = () => {
    setAdminResetSuccessMessage("");
    setAdminResetModal({
      error: "",
      isOpen: true,
      isSubmitting: false,
    });
  };

  const handleAdminPasswordResetClose = () => {
    setAdminResetModal({
      error: "",
      isOpen: false,
      isSubmitting: false,
    });
  };

  const handleAdminPasswordResetSubmit = async (payload) => {
    setAdminResetModal((current) => ({
      ...current,
      error: "",
      isSubmitting: true,
    }));

    try {
      await resetAdminPassword(payload);
      await loadAdminStatus();
      clearAdminAuth();
      setAdminAuthClearedAt(new Date().toISOString());
      setAdminResetSuccessMessage("관리자 비밀번호가 초기화되었습니다. 새 비밀번호로 다시 인증해 주세요.");
      setAdminResetModal({
        error: "",
        isOpen: false,
        isSubmitting: false,
      });
    } catch (error) {
      setAdminResetModal((current) => ({
        ...current,
        error: "초기화 코드 또는 입력값을 확인해 주세요.",
        isSubmitting: false,
      }));
    }
  };

  const handleClearAdminAuth = () => {
    clearAdminAuth();
    setAdminAuthClearedAt(new Date().toISOString());
  };

  const handleAdminPasswordSave = async (payload) => {
    const result = await updateAdminPassword(payload);
    await loadAdminStatus();
    clearAdminAuth();
    setAdminAuthClearedAt(new Date().toISOString());
    return result;
  };

  const handleMenuVisibilityChange = async (menuKey, isVisible) => {
    if (!isAdmin) throw new Error("관리자 권한이 필요합니다.");
    setMenuVisibilityError("");
    try {
      const response = await updateMenuVisibility(menuKey, isVisible);
      setMenuVisibility({ ...DEFAULT_MENU_VISIBILITY, ...(response?.visibility || {}) });
      if (!isVisible && SECTION_MENU_KEYS[activeSection] === menuKey) {
        setActiveSection("dashboard");
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    } catch (error) {
      setMenuVisibilityError(error?.message || "메뉴 표시 설정을 저장하지 못했습니다.");
      throw error;
    }
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

      {isAdmin ? <QuickAssetForm
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
      /> : null}

      <FilterBar
        canManage={isAdmin}
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
        sortControl={
          <SortSelect
            value={sortValue}
            options={ASSET_SORT_OPTIONS}
            onChange={setSortValue}
          />
        }
      />

      <AssetList
        assets={displayedAssets}
        isLoading={assetState.isLoading}
        error={assetState.error}
        hasActiveFilters={hasActiveFilters}
        selectedAssetId={selectedAssetId}
        onSelectAsset={setSelectedAssetId}
        categories={categories}
        activeCategoryId={filters.category_id}
        onCategorySelect={handleCategoryTabSelect}
        activeLocationGroup={filters.location_group}
        onLocationSelect={handleLocationTabSelect}
        onOpenCategoryCreate={() =>
          setCategoryCreateState({ isOpen: true, isSubmitting: false, error: "" })
        }
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
    if (accessDeniedSection || (!isAdmin && !allowedSections.has(activeSection))) {
      return (
        <section className="access-denied-card">
          <h2>접근 권한이 없습니다.</h2>
          <p>이 메뉴는 관리자만 사용할 수 있습니다.</p>
          <button type="button" onClick={() => handleNavigate("dashboard")}>대시보드로 이동</button>
        </section>
      );
    }
    if (activeSection === "assets") {
      return renderAssetManagement();
    }

    if (activeSection === "beverage-orders") {
      return <BeverageOrderPage />;
    }

    if (activeSection === "work-manuals") {
      return <WorkManualPage currentUser={currentUser} />;
    }

    if (activeSection === "vendor-contacts") {
      return <VendorContactsPage currentUser={currentUser} />;
    }

    if (activeSection === "expiration_schedules") {
      return <ExpirationSchedulePage currentUser={currentUser} />;
    }

    if (activeSection === "excel") {
      return renderExcelManagement();
    }

    if (activeSection === "software") {
      return <SoftwarePage />;
    }

    if (activeSection === "vehicles") {
      return <VehiclePage currentUser={currentUser} />;
    }

    if (activeSection === "paju-fire-insurance") {
      return <PajuFireInsurancePage currentUser={currentUser} />;
    }

    if (activeSection === "network") {
      return <NetworkStatusPage />;
    }

    if (activeSection === "stats") {
      return (
        <div className="portal-stats-page">
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
        </div>
      );
    }

    if (activeSection === "history") {
      return <HistoryPage />;
    }

    if (activeSection === "install-library") {
      return <InstallLibraryPage />;
    }

    if (activeSection === "hr-list") {
      return <HrAccountListPage currentUser={currentUser} />;
    }

    if (activeSection === "scm") {
      return <ScmPage />;
    }

    if (activeSection === "users") {
      return isAdmin ? <UserManagementPage currentUser={currentUser} /> : (
        <section className="access-denied-card"><h2>접근 권한이 없습니다.</h2></section>
      );
    }

    if (activeSection === "settings") {
      return (
        <SettingsPage
          backendStatus={backendStatus}
          menuVisibility={menuVisibility}
          menuVisibilityError={menuVisibilityError}
          onCheckBackend={checkBackend}
          onClearAdminAuth={handleClearAdminAuth}
          onAdminPasswordSave={handleAdminPasswordSave}
          onAdminPasswordResetRequest={handleAdminPasswordResetOpen}
          onMenuVisibilityChange={handleMenuVisibilityChange}
          onNavigate={handleNavigate}
          onProtectedMenuChange={handleProtectedMenuChange}
          adminStatus={adminStatus}
          adminAuthClearedAt={adminAuthClearedAt}
          adminResetSuccessMessage={adminResetSuccessMessage}
          protectedMenus={protectedMenus}
        />
      );
    }

    return (
      <DashboardPage onNavigate={handleNavigate} />
    );
  };

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((current) => {
      const nextValue = !current;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(nextValue));
      }
      return nextValue;
    });
  };

  return (
    <>
    <div className={isSidebarCollapsed ? "portal-shell portal-shell-sidebar-collapsed" : "portal-shell"}>
      <PortalSidebar
        activeSection={activeSection}
        collapsed={isSidebarCollapsed}
        menuVisibility={menuVisibility}
        allowedMenuIds={isAdmin ? null : Array.from(allowedSections)}
        isAdmin={isAdmin}
        onNavigate={handleNavigate}
      />

      <div className="portal-workspace">
        <header className="portal-topbar">
          <button
            type="button"
            className="icon-button portal-menu-button"
            aria-label={isSidebarCollapsed ? "사이드바 표시" : "사이드바 숨김"}
            aria-expanded={!isSidebarCollapsed}
            onClick={handleToggleSidebar}
          >
            ☰
          </button>
          <label className="portal-search" aria-label="통합 검색">
            <span aria-hidden="true">⌕</span>
            <input
              value={filters.keyword}
              onChange={(event) => setFilters({ ...filters, keyword: event.target.value })}
              onKeyDown={handlePortalSearchKeyDown}
              placeholder="자산 검색 (제품명, 시리얼번호, 모델명)"
            />
          </label>
          <div className="portal-topbar-actions">
            <ServerStatusPopover
              isOpen={isServerStatusOpen}
              onToggle={() => setIsServerStatusOpen((current) => !current)}
              onClose={() => setIsServerStatusOpen(false)}
              onCheck={checkBackend}
              status={backendStatus}
              visitorSummary={visitorSummary}
            />
            <div className="portal-notification-control" ref={notificationRef}>
              <button
                type="button"
                className="portal-alert-button"
                aria-label="최근 변경 이력 알림"
                aria-expanded={isNotificationOpen}
                onClick={() => setIsNotificationOpen((current) => !current)}
              >
                알림
              </button>
              {isNotificationOpen ? (
                <NotificationPopover
                  logs={notificationLogs}
                  state={notificationState}
                  onMore={() => {
                    setIsNotificationOpen(false);
                    handleNavigate("history");
                  }}
                  onScheduleMore={(item) => {
                    setIsNotificationOpen(false);
                    openExpirationScheduleFilter(item?.status);
                    handleNavigate("expiration_schedules");
                  }}
                />
              ) : null}
            </div>
            <span className="portal-header-action-divider" aria-hidden="true" />
            <div className="portal-header-profile" aria-label="현재 사용자">
              <strong>{currentUser?.name}</strong>
              <span>{isAdmin ? "Administrator" : "User"}</span>
            </div>
            <button
              type="button"
              className="portal-header-logout-button"
              onClick={onLogout}
            >
              로그아웃
            </button>
          </div>
        </header>

        <div
          className={
            activeSection === "stats"
              ? "portal-content portal-content-stats"
              : activeSection === "excel"
                || activeSection === "assets"
                || activeSection === "dashboard"
                || activeSection === "beverage-orders"
                || activeSection === "work-manuals"
                || activeSection === "vendor-contacts"
                || activeSection === "expiration_schedules"
                || activeSection === "software"
                || activeSection === "vehicles"
                || activeSection === "paju-fire-insurance"
                || activeSection === "network"
                || activeSection === "install-library"
                || activeSection === "hr-list"
                || activeSection === "scm"
                || activeSection === "users"
                ? "portal-content portal-content-wide"
                : "portal-content"
          }
        >
          <main className="portal-main">{renderActiveSection()}</main>

          {activeSection !== "assets" && activeSection !== "dashboard" && activeSection !== "beverage-orders" && activeSection !== "work-manuals" && activeSection !== "vendor-contacts" && activeSection !== "expiration_schedules" && activeSection !== "excel" && activeSection !== "software" && activeSection !== "vehicles" && activeSection !== "paju-fire-insurance" && activeSection !== "network" && activeSection !== "install-library" && activeSection !== "hr-list" && activeSection !== "scm" && activeSection !== "users" && (
            <aside className="portal-aside">
              <RecentActivityPanel onNavigate={handleNavigate} />
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
          currentUser={currentUser}
        />
      )}

      {isAdmin ? <AssetForm
        categories={categories}
        departments={departments}
        lookupState={lookupState}
        isOpen={isFormOpen}
        isSubmitting={isSubmitting}
        error={formError}
        onClose={() => setIsFormOpen(false)}
        onSubmit={handleCreateAsset}
      /> : null}

      {isAdmin ? <CategoryCreateModal
        isOpen={categoryCreateState.isOpen}
        error={categoryCreateState.error}
        isSubmitting={categoryCreateState.isSubmitting}
        onClose={() =>
          setCategoryCreateState({ isOpen: false, isSubmitting: false, error: "" })
        }
        onSubmit={handleCreateCategory}
      /> : null}
      <AdminAuthModal
        error={adminAuthModal.error}
        isOpen={adminAuthModal.isOpen}
        isSubmitting={adminAuthModal.isSubmitting}
        menuLabel={MENU_LABELS[adminAuthModal.targetSection] || "보호 메뉴"}
        onCancel={handleAdminAuthCancel}
        onPasswordResetRequest={handleAdminPasswordResetOpen}
        onSubmit={handleAdminAuthSubmit}
        resetSuccessMessage={adminResetSuccessMessage}
      />
      <AdminPasswordResetModal
        error={adminResetModal.error}
        isOpen={adminResetModal.isOpen}
        isSubmitting={adminResetModal.isSubmitting}
        onClose={handleAdminPasswordResetClose}
        onSubmit={handleAdminPasswordResetSubmit}
      />
    </div>
    </>
  );
}

function NotificationPopover({ logs, onMore, onScheduleMore, state }) {
  return (
    <section className="notification-popover" aria-label="최근 변경 이력 알림">
      <div className="notification-popover-heading">
        <h3>알림</h3>
        <button type="button" className="link-button" onClick={onMore}>
          더보기
        </button>
      </div>
      {state.isLoading ? (
        <div className="notification-empty">불러오는 중입니다.</div>
      ) : state.error ? (
        <div className="notification-empty">최근 변경 이력을 불러오지 못했습니다.</div>
      ) : logs.length === 0 ? (
        <div className="notification-empty">최근 알림이 없습니다.</div>
      ) : (
        <div className="notification-list">
          {logs.map((log) => (
            <button
              type="button"
              className="notification-item"
              key={log.id}
              onClick={() => {
                if (log.notification_type === "expiration") {
                  onScheduleMore?.(log);
                  return;
                }
                onMore?.();
              }}
            >
              <span className={`notification-action-badge notification-action-${getNotificationActionTone(log.action_type)}`}>
                {getNotificationActionLabel(log.action_type)}
              </span>
              <strong title={formatNotificationTitle(log)}>
                {formatNotificationTitle(log)}
              </strong>
              <time dateTime={log.created_at || ""}>{formatNotificationDateTime(log.created_at)}</time>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function getNotificationActionLabel(actionType) {
  const normalizedType = String(actionType || "").toLowerCase();
  const labelMap = {
    create: "등록",
    register: "등록",
    update: "수정",
    edit: "수정",
    delete: "삭제",
    remove: "삭제",
    dispose: "폐기",
    "reveal-password": "확인",
    reveal_password: "확인",
    view: "조회",
    read: "조회",
    login: "접속",
    expiration_overdue: "기한 초과",
    expiration_due: "점검 예정",
    unknown: "기타",
  };
  return labelMap[normalizedType] || "기타";
}

function getNotificationActionTone(actionType) {
  const label = getNotificationActionLabel(actionType);
  if (label === "삭제" || label === "폐기") {
    return "danger";
  }
  if (label === "기한 초과") {
    return "danger";
  }
  if (label === "점검 예정") {
    return "warning";
  }
  if (label === "수정") {
    return "warning";
  }
  if (label === "확인" || label === "조회" || label === "접속") {
    return "neutral";
  }
  return "success";
}

function formatNotificationTitle(log) {
  if (log?.notification_type === "expiration") {
    return log.summary || log.target_name || "-";
  }
  const summary = formatNotificationText(log?.summary || log?.target_name);
  const actionLabel = getNotificationActionLabel(log?.action_type);
  if (String(log?.action_type || "").toLowerCase().includes("reveal")) {
    return `접속정보 비밀번호 확인: ${summary}`;
  }
  return `${actionLabel}: ${summary}`;
}

function buildExpirationNotificationItems(items) {
  const statusPriority = {
    overdue: 0,
    within_7_days: 1,
    within_30_days: 2,
  };
  return (Array.isArray(items) ? items : [])
    .filter((item) => ["overdue", "within_7_days", "within_30_days"].includes(item.status))
    .sort((left, right) => {
      const leftPriority = statusPriority[left.status] ?? 9;
      const rightPriority = statusPriority[right.status] ?? 9;
      if (leftPriority !== rightPriority) {
        return leftPriority - rightPriority;
      }
      return String(left.due_date || "").localeCompare(String(right.due_date || ""));
    })
    .slice(0, 5)
    .map((item) => ({
      id: `expiration-${item.id}`,
      notification_type: "expiration",
      action_type: item.status === "overdue" ? "expiration_overdue" : "expiration_due",
      status: item.status,
      summary: `${getCategoryLabel(item.category)} · ${formatNotificationText(item.target_name)} · ${formatDaysLeft(item)}`,
      target_name: item.title,
      created_at: item.due_date,
    }));
}

function formatNotificationText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatNotificationDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  const datePart = new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  }).format(date).replace(/\s/g, "");
  const timePart = new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
  return `${datePart} ${timePart}`;
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

function getStoredProtectedMenus() {
  if (typeof window === "undefined") {
    return DEFAULT_PROTECTED_MENUS;
  }

  try {
    const storedValue = window.localStorage.getItem(PROTECTED_MENU_STORAGE_KEY);
    if (!storedValue) {
      return DEFAULT_PROTECTED_MENUS;
    }

    const parsedValue = JSON.parse(storedValue);
    return Object.keys(DEFAULT_PROTECTED_MENUS).reduce(
      (protectedMenuMap, menuId) => ({
        ...protectedMenuMap,
        [menuId]:
          typeof parsedValue?.[menuId] === "boolean"
            ? parsedValue[menuId]
            : DEFAULT_PROTECTED_MENUS[menuId],
      }),
      {},
    );
  } catch {
    return DEFAULT_PROTECTED_MENUS;
  }
}

function hasValidAdminAuth() {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const storedValue = window.sessionStorage.getItem(ADMIN_AUTH_STORAGE_KEY);
    if (!storedValue) {
      return false;
    }

    const parsedValue = JSON.parse(storedValue);
    const expiresAt = Date.parse(parsedValue?.expires_at || "");
    if (!parsedValue?.token || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      clearAdminAuth();
      return false;
    }

    return true;
  } catch {
    clearAdminAuth();
    return false;
  }
}

function saveAdminAuth(authResult) {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    ADMIN_AUTH_STORAGE_KEY,
    JSON.stringify({
      token: authResult.token,
      expires_at: authResult.expires_at,
    }),
  );
}

function clearAdminAuth() {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(ADMIN_AUTH_STORAGE_KEY);
}

export default App;
