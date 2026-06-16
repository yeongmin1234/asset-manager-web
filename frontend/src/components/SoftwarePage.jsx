import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createSoftwareItem,
  deleteSoftwareItem,
  getSoftwareItems,
  getSoftwareStatsSummary,
  updateSoftwareItem,
} from "../api/client.js";
import SoftwareList from "./SoftwareList.jsx";
import SoftwareQuickForm from "./SoftwareQuickForm.jsx";
import SoftwareStats from "./SoftwareStats.jsx";

const INITIAL_FILTERS = {
  expiration_status: "",
};

const SOFTWARE_TABS = [
  { label: "전체", value: "" },
  { label: "영구", value: "영구" },
  { label: "구독", value: "구독" },
  { label: "사용중지", value: "사용중지" },
];

const INITIAL_SUMMARY = {
  total_software: 0,
  perpetual_count: 0,
  subscription_count: 0,
  discontinued_count: 0,
};

function SoftwarePage() {
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [items, setItems] = useState([]);
  const [listState, setListState] = useState({ isLoading: false, error: "" });
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [summaryState, setSummaryState] = useState({ isLoading: false, error: "" });
  const [editingItem, setEditingItem] = useState(null);
  const [activeTab, setActiveTab] = useState("");

  const displayedItems = useMemo(
    () => filterSoftwareItems(items, activeTab, filters.expiration_status),
    [activeTab, filters.expiration_status, items],
  );

  const expirationSummary = useMemo(
    () => getExpirationSummary(items),
    [items],
  );

  const loadItems = useCallback(async () => {
    setListState({ isLoading: true, error: "" });
    try {
      setItems(await getSoftwareItems());
      setListState({ isLoading: false, error: "" });
    } catch (error) {
      setItems([]);
      setListState({ isLoading: false, error: error.message });
    }
  }, []);

  const loadSummary = useCallback(async () => {
    setSummaryState({ isLoading: true, error: "" });
    try {
      setSummary({ ...INITIAL_SUMMARY, ...(await getSoftwareStatsSummary()) });
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
      await updateSoftwareItem(editingItem.id, payload);
      setEditingItem(null);
    } else {
      await createSoftwareItem(payload);
    }
    await Promise.all([loadItems(), loadSummary()]);
  };

  const handleDelete = async (item) => {
    const confirmed = window.confirm(`${item.name} 항목을 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    await deleteSoftwareItem(item.id);
    if (editingItem?.id === item.id) {
      setEditingItem(null);
    }
    await Promise.all([loadItems(), loadSummary()]);
  };

  return (
    <>
      <div className="portal-screen-heading">
        <h2>SW 현황</h2>
        <p>사내 소프트웨어, 라이선스, 구독 현황을 관리합니다.</p>
      </div>
      <SoftwareStats
        summary={summary}
        expirationSummary={expirationSummary}
        isLoading={summaryState.isLoading}
        error={summaryState.error}
      />
      <SoftwareQuickForm
        editingItem={editingItem}
        onCancelEdit={() => setEditingItem(null)}
        onSubmit={handleSubmit}
      />
      <SoftwareList
        items={displayedItems}
        isLoading={listState.isLoading}
        error={listState.error}
        filters={filters}
        activeTab={activeTab}
        editingItemId={editingItem?.id || null}
        onDelete={handleDelete}
        onEdit={setEditingItem}
        onFilterChange={setFilters}
        onTabChange={setActiveTab}
        tabs={SOFTWARE_TABS}
      />
    </>
  );
}

function filterSoftwareItems(items, licenseType, expirationStatus) {
  const safeItems = Array.isArray(items) ? items : [];

  return safeItems.filter((item) => {
    if (licenseType && item.license_type !== licenseType) {
      return false;
    }
    if (!expirationStatus) {
      return true;
    }

    const daysLeft = getDaysUntilExpire(item.expire_date);
    if (expirationStatus === "no_date") {
      return daysLeft === null;
    }
    if (daysLeft === null) {
      return false;
    }
    if (expirationStatus === "expired") {
      return daysLeft < 0;
    }
    if (expirationStatus === "within_30") {
      return daysLeft >= 0 && daysLeft <= 30;
    }
    if (expirationStatus === "within_60") {
      return daysLeft >= 0 && daysLeft <= 60;
    }
    if (expirationStatus === "within_90") {
      return daysLeft >= 0 && daysLeft <= 90;
    }
    return true;
  });
}

function getExpirationSummary(items) {
  return (Array.isArray(items) ? items : []).reduce(
    (summary, item) => {
      const daysLeft = getDaysUntilExpire(item.expire_date);
      if (daysLeft === null) {
        return summary;
      }
      if (daysLeft < 0) {
        return { ...summary, expiredCount: summary.expiredCount + 1 };
      }
      if (daysLeft <= 30) {
        return { ...summary, within30Count: summary.within30Count + 1 };
      }
      return summary;
    },
    { expiredCount: 0, within30Count: 0 },
  );
}

function getDaysUntilExpire(expireDate) {
  if (!expireDate) {
    return null;
  }

  const [year, month, day] = String(expireDate).split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const expireStart = new Date(year, month - 1, day);
  return Math.ceil((expireStart.getTime() - todayStart.getTime()) / 86400000);
}

export default SoftwarePage;
