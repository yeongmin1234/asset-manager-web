import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createVehicle,
  deleteVehicle,
  getVehicleSummary,
  getVehicles,
  updateVehicle,
} from "../api/client.js";
import VehicleList, { getDaysUntilDate } from "./VehicleList.jsx";
import VehicleInsuranceHistory from "./VehicleInsuranceHistory.jsx";
import VehicleQuickForm from "./VehicleQuickForm.jsx";
import VehicleStats from "./VehicleStats.jsx";

const INITIAL_SUMMARY = {
  total_vehicles: 0,
  company_owned_count: 0,
  lease_count: 0,
  expiring_soon_count: 0,
};

const VEHICLE_TABS = [
  { label: "전체", value: "" },
  { label: "회사 소유", value: "회사" },
  { label: "리스", value: "리스" },
  { label: "보험 만기 임박", value: "insurance_expiring" },
  { label: "리스 만기 임박", value: "lease_expiring" },
];

const VEHICLE_COMPANY_TABS = [
  { label: "전체", value: "" },
  { label: "더리모", value: "더리모" },
  { label: "한국리모텍", value: "한국리모텍" },
];

function VehiclePage() {
  const [items, setItems] = useState([]);
  const [listState, setListState] = useState({ isLoading: false, error: "" });
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [summaryState, setSummaryState] = useState({ isLoading: false, error: "" });
  const [editingItem, setEditingItem] = useState(null);
  const [activeTab, setActiveTab] = useState("");
  const [activeCompanyTab, setActiveCompanyTab] = useState("");
  const [activePageTab, setActivePageTab] = useState("list");

  const displayedItems = useMemo(
    () => filterVehicles(items, activeTab, activeCompanyTab),
    [activeCompanyTab, activeTab, items],
  );

  const loadItems = useCallback(async () => {
    setListState({ isLoading: true, error: "" });
    try {
      setItems(await getVehicles());
      setListState({ isLoading: false, error: "" });
    } catch (error) {
      setItems([]);
      setListState({ isLoading: false, error: error.message });
    }
  }, []);

  const loadSummary = useCallback(async () => {
    setSummaryState({ isLoading: true, error: "" });
    try {
      setSummary({ ...INITIAL_SUMMARY, ...(await getVehicleSummary()) });
      setSummaryState({ isLoading: false, error: "" });
    } catch (error) {
      setSummary(INITIAL_SUMMARY);
      setSummaryState({ isLoading: false, error: error.message });
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleSubmit = async (payload) => {
    if (editingItem) {
      await updateVehicle(editingItem.id, payload);
      setEditingItem(null);
    } else {
      await createVehicle(payload);
    }
    await Promise.all([loadItems(), loadSummary()]);
    setActivePageTab("list");
  };

  const handleDelete = async (item) => {
    const confirmed = window.confirm(`${item.vehicle_number} 차량을 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    await deleteVehicle(item.id);
    if (editingItem?.id === item.id) {
      setEditingItem(null);
    }
    await Promise.all([loadItems(), loadSummary()]);
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setActivePageTab("form");
  };

  const handleCancelEdit = () => {
    setEditingItem(null);
    setActivePageTab("list");
  };

  const renderPageTabs = () => (
    <div className="vehicle-page-tabs" aria-label="법인차량 화면 탭">
      <button
        type="button"
        className={activePageTab === "list" ? "vehicle-page-tab active" : "vehicle-page-tab"}
        onClick={() => setActivePageTab("list")}
      >
        차량 목록
      </button>
      <button
        type="button"
        className={activePageTab === "form" ? "vehicle-page-tab active" : "vehicle-page-tab"}
        onClick={() => setActivePageTab("form")}
      >
        빠른 등록
      </button>
      <button
        type="button"
        className={activePageTab === "history" ? "vehicle-page-tab active" : "vehicle-page-tab"}
        onClick={() => setActivePageTab("history")}
      >
        보험 이력
      </button>
    </div>
  );

  return (
    <div className="vehicle-page">
      <div className="portal-screen-heading vehicle-page-heading">
        <div>
          <h2>법인차량 관리</h2>
          <p>회사 법인차량, 보험, 리스 만기 정보를 관리합니다.</p>
        </div>
        <VehicleStats
          summary={summary}
          isLoading={summaryState.isLoading}
          error={summaryState.error}
          compact
        />
      </div>

      <section className="content-panel vehicle-main-panel">
        {renderPageTabs()}

        <div className={`vehicle-tab-content vehicle-tab-content-${activePageTab}`}>
          {activePageTab === "list" ? (
            <VehicleList
              items={displayedItems}
              isLoading={listState.isLoading}
              error={listState.error}
              activeTab={activeTab}
              activeCompanyTab={activeCompanyTab}
              companyTabs={VEHICLE_COMPANY_TABS}
              editingItemId={editingItem?.id || null}
              onDelete={handleDelete}
              onEdit={handleEdit}
              onCompanyTabChange={setActiveCompanyTab}
              onTabChange={setActiveTab}
              tabs={VEHICLE_TABS}
            />
          ) : activePageTab === "history" ? (
            <VehicleInsuranceHistory vehicles={items} />
          ) : (
            <VehicleQuickForm
              editingItem={editingItem}
              onCancelEdit={handleCancelEdit}
              onSubmit={handleSubmit}
              showHeading={false}
            />
          )}
        </div>
      </section>
    </div>
  );
}

function filterVehicles(items, activeTab, activeCompanyTab) {
  const safeItems = Array.isArray(items) ? items : [];
  return safeItems.filter((item) => {
    if (activeCompanyTab && item.company_name !== activeCompanyTab) {
      return false;
    }
    if (!activeTab) {
      return true;
    }
    if (activeTab === "회사" || activeTab === "리스") {
      return item.ownership_type === activeTab;
    }
    if (activeTab === "insurance_expiring") {
      const daysLeft = getDaysUntilDate(item.insurance_end_date);
      return daysLeft !== null && daysLeft >= 0 && daysLeft <= 30;
    }
    if (activeTab === "lease_expiring") {
      const daysLeft = getDaysUntilDate(item.lease_end_date);
      return daysLeft !== null && daysLeft >= 0 && daysLeft <= 60;
    }
    return true;
  });
}

export default VehiclePage;
