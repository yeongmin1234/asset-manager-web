import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  getNetworkStatus,
  getRecentActivityLogs,
  getSoftwareItems,
  getSoftwareStatsSummary,
  getStatsSummary,
  getVehicleSummary,
} from "../api/client.js";

const EMPTY_ASSET_SUMMARY = {
  total_assets: 0,
  in_use_assets: 0,
  unused_assets: 0,
  disposed_assets: 0,
};

const EMPTY_SOFTWARE_SUMMARY = {
  total_software: 0,
  perpetual_count: 0,
  subscription_count: 0,
  discontinued_count: 0,
};

const EMPTY_VEHICLE_SUMMARY = {
  total_vehicles: 0,
  company_owned_count: 0,
  lease_count: 0,
  expiring_soon_count: 0,
};

const EMPTY_NETWORK_SUMMARY = {
  total: 0,
  ok: 0,
  warning: 0,
  down: 0,
};

function DashboardPage({ onNavigate }) {
  const [assetSummary, setAssetSummary] = useState(EMPTY_ASSET_SUMMARY);
  const [softwareSummary, setSoftwareSummary] = useState(EMPTY_SOFTWARE_SUMMARY);
  const [softwareItems, setSoftwareItems] = useState([]);
  const [vehicleSummary, setVehicleSummary] = useState(EMPTY_VEHICLE_SUMMARY);
  const [networkStatus, setNetworkStatus] = useState({
    items: [],
    summary: EMPTY_NETWORK_SUMMARY,
    checkedAt: "",
    error: "",
  });
  const [recentLogs, setRecentLogs] = useState([]);
  const [dashboardState, setDashboardState] = useState({ isLoading: false, error: "" });

  const loadDashboard = useCallback(async () => {
    setDashboardState({ isLoading: true, error: "" });

    const [
      assetResult,
      softwareResult,
      softwareItemsResult,
      vehicleResult,
      networkResult,
      recentLogResult,
    ] = await Promise.allSettled([
      getStatsSummary(),
      getSoftwareStatsSummary(),
      getSoftwareItems(),
      getVehicleSummary(),
      getNetworkStatus(),
      getRecentActivityLogs(30),
    ]);

    if (assetResult.status === "fulfilled") {
      setAssetSummary({ ...EMPTY_ASSET_SUMMARY, ...(assetResult.value || {}) });
    } else {
      setAssetSummary(EMPTY_ASSET_SUMMARY);
    }

    if (softwareResult.status === "fulfilled") {
      setSoftwareSummary({ ...EMPTY_SOFTWARE_SUMMARY, ...(softwareResult.value || {}) });
    } else {
      setSoftwareSummary(EMPTY_SOFTWARE_SUMMARY);
    }

    if (softwareItemsResult.status === "fulfilled") {
      setSoftwareItems(Array.isArray(softwareItemsResult.value) ? softwareItemsResult.value : []);
    } else {
      setSoftwareItems([]);
    }

    if (vehicleResult.status === "fulfilled") {
      setVehicleSummary({ ...EMPTY_VEHICLE_SUMMARY, ...(vehicleResult.value || {}) });
    } else {
      setVehicleSummary(EMPTY_VEHICLE_SUMMARY);
    }

    if (networkResult.status === "fulfilled") {
      const data = networkResult.value || {};
      const items = Array.isArray(data.items) ? data.items : [];
      setNetworkStatus({
        items,
        summary: { ...EMPTY_NETWORK_SUMMARY, ...(data.summary || {}) },
        checkedAt: getNetworkCheckedAt(data),
        error: "",
      });
    } else {
      setNetworkStatus({
        items: [],
        summary: EMPTY_NETWORK_SUMMARY,
        checkedAt: "",
        error: networkResult.reason?.message || "네트워크 상태 확인 필요",
      });
    }

    if (recentLogResult.status === "fulfilled") {
      setRecentLogs(Array.isArray(recentLogResult.value) ? recentLogResult.value : []);
    } else {
      setRecentLogs([]);
    }

    setDashboardState({
      isLoading: false,
      error: getDashboardError([
        assetResult,
        softwareResult,
        vehicleResult,
        networkResult,
        recentLogResult,
      ]),
    });
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const softwareExpireSoonCount = useMemo(
    () => countSoftwareExpiringSoon(softwareItems),
    [softwareItems],
  );

  const attentionItems = useMemo(
    () =>
      buildAttentionItems({
        vehicleSummary,
        softwareExpireSoonCount,
        networkStatus,
        recentLogs,
      }),
    [networkStatus, recentLogs, softwareExpireSoonCount, vehicleSummary],
  );

  const displayedRecentLogs = useMemo(
    () => recentLogs.slice(0, 6),
    [recentLogs],
  );

  const recentInsuranceLogs = useMemo(
    () => recentLogs.filter(isVehicleInsuranceLog).slice(0, 4),
    [recentLogs],
  );

  const summaryGroups = useMemo(
    () => [
      {
        title: "자산",
        tone: "blue",
        action: "assets",
        rows: [
          ["전체 자산", assetSummary.total_assets],
          ["사용중", assetSummary.in_use_assets],
          ["미사용", assetSummary.unused_assets],
          ["폐기", assetSummary.disposed_assets],
        ],
      },
      {
        title: "SW",
        tone: "green",
        action: "software",
        rows: [
          ["전체 SW", softwareSummary.total_software],
          ["영구", softwareSummary.perpetual_count],
          ["구독", softwareSummary.subscription_count],
          ["사용중지", softwareSummary.discontinued_count],
        ],
      },
      {
        title: "법인차량",
        tone: "amber",
        action: "vehicles",
        rows: [
          ["전체 차량", vehicleSummary.total_vehicles],
          ["회사 소유", vehicleSummary.company_owned_count],
          ["리스", vehicleSummary.lease_count],
          ["만료 임박", vehicleSummary.expiring_soon_count],
        ],
      },
      {
        title: "네트워크",
        tone: networkStatus.summary.down ? "red" : networkStatus.summary.warning ? "amber" : "green",
        action: "network",
        rows: [
          ["정상", networkStatus.summary.ok],
          ["주의", networkStatus.summary.warning],
          ["장애", networkStatus.summary.down],
          ["마지막 확인", networkStatus.checkedAt ? formatTime(networkStatus.checkedAt) : "확인 필요"],
        ],
      },
    ],
    [assetSummary, networkStatus, softwareSummary, vehicleSummary],
  );

  return (
    <section className="dashboard-page" aria-labelledby="dashboard-title">
      <div className="dashboard-hero-compact">
        <div>
          <span className="section-kicker">Operations Dashboard</span>
          <h2 id="dashboard-title">안녕하세요, 관리자님!</h2>
          <p>자산, SW, 차량, 네트워크 상태를 한 화면에서 확인합니다.</p>
        </div>
        <div className="dashboard-quick-actions">
          <button type="button" className="primary-action" onClick={() => onNavigate?.("quick")}>
            빠른 등록
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("assets")}>
            자산 목록
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("software")}>
            SW 현황
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("vehicles")}>
            법인차량
          </button>
          <button type="button" className="secondary-button" onClick={() => onNavigate?.("network")}>
            네트워크 현황
          </button>
        </div>
      </div>

      {dashboardState.error ? (
        <div className="dashboard-inline-alert">{dashboardState.error}</div>
      ) : null}

      <div className="dashboard-summary-grid">
        {summaryGroups.map((group) => (
          <article className={`dashboard-summary-card dashboard-summary-card-${group.tone}`} key={group.title}>
            <div className="dashboard-card-heading">
              <h3>{group.title}</h3>
              <button type="button" className="link-button" onClick={() => onNavigate?.(group.action)}>
                보기
              </button>
            </div>
            <dl>
              {group.rows.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{formatCount(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>

      <div className="dashboard-work-grid">
        <section className="dashboard-panel dashboard-attention-panel">
          <div className="dashboard-panel-heading">
            <h3>주의 항목</h3>
            <button type="button" className="link-button" onClick={loadDashboard}>
              새로고침
            </button>
          </div>

          {dashboardState.isLoading ? (
            <div className="dashboard-empty">운영 현황을 불러오는 중입니다.</div>
          ) : attentionItems.length === 0 ? (
            <div className="dashboard-empty">현재 주의 항목이 없습니다.</div>
          ) : (
            <ul className="dashboard-attention-list">
              {attentionItems.map((item) => (
                <li key={item.id}>
                  <span className={`dashboard-attention-dot dashboard-attention-dot-${item.tone}`} />
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dashboard-panel dashboard-recent-panel">
          <div className="dashboard-panel-heading">
            <h3>최근 변경 이력</h3>
            <button type="button" className="link-button" onClick={() => onNavigate?.("history")}>
              더보기
            </button>
          </div>

          {displayedRecentLogs.length === 0 ? (
            <div className="dashboard-empty">최근 변경 이력이 없습니다.</div>
          ) : (
            <div className="dashboard-recent-list">
              {displayedRecentLogs.map((log) => (
                <div className="dashboard-recent-item" key={log.id}>
                  <span className="dashboard-recent-module">{getLogModuleLabel(log)}</span>
                  <em className={`dashboard-action-badge dashboard-action-badge-${getActionTone(log.action_type)}`}>
                    {getActionLabel(log.action_type)}
                  </em>
                  <div className="dashboard-recent-summary">
                    <strong title={formatText(log.summary || log.target_name)}>
                      {formatText(log.summary || log.target_name)}
                    </strong>
                    <p>
                      {formatDateTime(log.created_at)}
                      {getActorLabel(log) ? ` · ${getActorLabel(log)}` : ""}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="dashboard-insurance-recent">
            <div className="dashboard-insurance-recent-heading">
              <h4>최근 보험 이력</h4>
              <span>등록/수정/삭제</span>
            </div>
            {recentInsuranceLogs.length === 0 ? (
              <div className="dashboard-insurance-empty">최근 보험 이력이 없습니다.</div>
            ) : (
              <div className="dashboard-insurance-list">
                {recentInsuranceLogs.map((log) => (
                  <div className="dashboard-insurance-item" key={`insurance-${log.id}`}>
                    <em className={`dashboard-action-badge dashboard-action-badge-${getActionTone(log.action_type)}`}>
                      {getActionLabel(log.action_type)}
                    </em>
                    <strong title={formatText(log.summary || log.target_name)}>
                      {formatText(log.summary || log.target_name)}
                    </strong>
                    <span>{formatDateTime(log.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}

function getLogCategory(log) {
  const haystack = [
    log?.menu_name,
    log?.target_type,
    log?.target_name,
    log?.summary,
    log?.description,
    log?.action_type,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (haystack.includes("차량 보험 이력") || haystack.includes("보험 이력")) {
    return "vehicle-insurance";
  }
  if (haystack.includes("법인차량") || haystack.includes("차량") || haystack.includes("vehicle")) {
    return "vehicle";
  }
  if (haystack.includes("software") || haystack.includes("sw") || haystack.includes("소프트웨어")) {
    return "software";
  }
  if (haystack.includes("음료") || haystack.includes("beverage")) {
    return "beverage";
  }
  if (haystack.includes("설정") || haystack.includes("admin") || haystack.includes("settings")) {
    return "settings";
  }
  return "asset";
}

function isVehicleInsuranceLog(log) {
  return getLogCategory(log) === "vehicle-insurance";
}

function getLogModuleLabel(log) {
  const category = getLogCategory(log);
  const labelMap = {
    asset: "자산",
    software: "SW",
    vehicle: "법인차량",
    "vehicle-insurance": "보험 이력",
    beverage: "음료",
    settings: "설정",
  };
  return labelMap[category] || formatText(log?.menu_name);
}

function getActorLabel(log) {
  return (
    log?.actor_name ||
    log?.actor ||
    log?.user_name ||
    log?.admin_name ||
    log?.created_by ||
    ""
  );
}

function getActionTone(actionType) {
  if (actionType === "delete" || actionType === "dispose") {
    return "danger";
  }
  if (actionType === "update") {
    return "warning";
  }
  return "success";
}

function buildAttentionItems({ vehicleSummary, softwareExpireSoonCount, networkStatus, recentLogs }) {
  const items = [];
  const vehicleExpiringCount = Number(vehicleSummary.expiring_soon_count || 0);

  if (vehicleExpiringCount > 0) {
    items.push({
      id: "vehicle-expiring",
      title: "차량 만료 임박",
      description: `보험/리스 만료 임박 차량 ${vehicleExpiringCount.toLocaleString("ko-KR")}대`,
      tone: "warning",
    });
  }

  if (softwareExpireSoonCount > 0) {
    items.push({
      id: "software-expiring",
      title: "SW 구독 만료 임박",
      description: `30일 이내 만료 예정 SW ${softwareExpireSoonCount.toLocaleString("ko-KR")}개`,
      tone: "warning",
    });
  }

  const networkProblemItems = networkStatus.items.filter((item) => item.status === "warning" || item.status === "down");
  networkProblemItems.slice(0, 3).forEach((item) => {
    items.push({
      id: `network-${item.name}-${item.target}`,
      title: `네트워크 ${item.status === "down" ? "장애" : "주의"}`,
      description: `${formatText(item.name)} · ${formatText(item.target)}`,
      tone: item.status === "down" ? "danger" : "warning",
    });
  });

  const recentRiskLog = recentLogs.find((log) => log.action_type === "delete" || log.action_type === "dispose");
  if (recentRiskLog) {
    items.push({
      id: `recent-risk-${recentRiskLog.id}`,
      title: "최근 삭제/폐기 작업",
      description: `${formatText(recentRiskLog.menu_name)} · ${formatText(recentRiskLog.summary || recentRiskLog.target_name)}`,
      tone: "neutral",
    });
  }

  return items.slice(0, 6);
}

function countSoftwareExpiringSoon(items) {
  return (Array.isArray(items) ? items : []).filter((item) => {
    const daysLeft = getDaysUntilExpire(item.expire_date);
    return daysLeft !== null && daysLeft >= 0 && daysLeft <= 30;
  }).length;
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

function getNetworkCheckedAt(data) {
  if (Array.isArray(data?.recent_checks) && data.recent_checks[0]?.checked_at) {
    return data.recent_checks[0].checked_at;
  }
  if (Array.isArray(data?.items) && data.items[0]?.checked_at) {
    return data.items[0].checked_at;
  }
  return "";
}

function getDashboardError(results) {
  const failedCount = results.filter((result) => result.status === "rejected").length;
  if (!failedCount) {
    return "";
  }
  return `일부 운영 현황을 불러오지 못했습니다. (${failedCount}건)`;
}

function getActionLabel(actionType) {
  const labelMap = {
    create: "등록",
    update: "수정",
    delete: "삭제",
    dispose: "폐기",
  };
  return labelMap[actionType] || formatText(actionType);
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatCount(value) {
  if (typeof value === "string") {
    return value;
  }
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default DashboardPage;
