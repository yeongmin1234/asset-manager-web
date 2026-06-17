import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createVehicle,
  deleteVehicle,
  getVehicleSummary,
  getVehicles,
  updateVehicle,
} from "../api/client.js";
import VehicleList, { getDaysUntilDate } from "./VehicleList.jsx";
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

function VehiclePage() {
  const [items, setItems] = useState([]);
  const [listState, setListState] = useState({ isLoading: false, error: "" });
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [summaryState, setSummaryState] = useState({ isLoading: false, error: "" });
  const [editingItem, setEditingItem] = useState(null);
  const [activeTab, setActiveTab] = useState("");
  const [activePageTab, setActivePageTab] = useState("list");

  const displayedItems = useMemo(
    () => filterVehicles(items, activeTab),
    [activeTab, items],
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
    </div>
  );

  return (
    <>
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
        <div className="section-heading vehicle-main-heading">
          <div>
            <h2>{activePageTab === "list" ? "차량 목록" : editingItem ? "차량 수정" : "빠른 등록"}</h2>
            <p>
              {activePageTab === "list"
                ? "보험 중심 목록으로 확인하고, 리스 정보는 리스 상세에서 확인합니다."
                : "법인차량과 보험/리스 정보를 등록합니다."}
            </p>
          </div>
        </div>

        {renderPageTabs()}

        <div className="vehicle-tab-content">
          {activePageTab === "list" ? (
            <VehicleList
              items={displayedItems}
              isLoading={listState.isLoading}
              error={listState.error}
              activeTab={activeTab}
              editingItemId={editingItem?.id || null}
              onDelete={handleDelete}
              onEdit={handleEdit}
              onTabChange={setActiveTab}
              tabs={VEHICLE_TABS}
            />
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
    </>
  );
}

function filterVehicles(items, activeTab) {
  const safeItems = Array.isArray(items) ? items : [];
  if (!activeTab) {
    return safeItems;
  }
  return safeItems.filter((item) => {
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
