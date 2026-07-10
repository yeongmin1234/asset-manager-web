import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createDashboardNotice,
  deleteDashboardNotice,
  getDashboardNotices,
  getExpirationScheduleSummary,
  getNetworkStatus,
  getRecentActivityLogs,
  getSoftwareItems,
  getSoftwareStatsSummary,
  getStatsSummary,
  getVehicleSummary,
  updateDashboardNotice,
} from "../api/client.js";
import { formatDaysLeft, getCategoryLabel, openExpirationScheduleFilter } from "./ExpirationSchedulePage.jsx";
import {
  BOARD_SORT_OPTIONS,
  SORT_VALUES,
  SortSelect,
  sortItems,
} from "../utils/sortOptions.jsx";

const NOTICE_TYPES = ["공지", "업데이트", "점검", "기타"];
const EMPTY_NOTICE_FORM = {
  notice_type: "공지",
  title: "",
  content: "",
  is_pinned: false,
  admin_password: "",
};

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

const EMPTY_EXPIRATION_SUMMARY = {
  overdue_count: 0,
  within_7_days_count: 0,
  within_30_days_count: 0,
  normal_count: 0,
  completed_count: 0,
  upcoming_items: [],
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
  const [expirationSummary, setExpirationSummary] = useState(EMPTY_EXPIRATION_SUMMARY);
  const [recentLogs, setRecentLogs] = useState([]);
  const [dashboardNotices, setDashboardNotices] = useState([]);
  const [noticeFormState, setNoticeFormState] = useState({
    error: "",
    isOpen: false,
    isSubmitting: false,
    notice: null,
  });
  const [noticeDetail, setNoticeDetail] = useState(null);
  const [noticeDeleteState, setNoticeDeleteState] = useState({
    adminPassword: "",
    error: "",
    isOpen: false,
    isSubmitting: false,
    notice: null,
  });
  const [noticeAdminUnlocked, setNoticeAdminUnlocked] = useState(false);
  const [dashboardState, setDashboardState] = useState({ isLoading: false, error: "" });
  const [noticeSortValue, setNoticeSortValue] = useState(SORT_VALUES.latest);

  const loadDashboard = useCallback(async () => {
    setDashboardState({ isLoading: true, error: "" });

    const [
      assetResult,
      softwareResult,
      softwareItemsResult,
      vehicleResult,
      networkResult,
      recentLogResult,
      noticesResult,
      expirationResult,
    ] = await Promise.allSettled([
      getStatsSummary(),
      getSoftwareStatsSummary(),
      getSoftwareItems(),
      getVehicleSummary(),
      getNetworkStatus(),
      getRecentActivityLogs(30),
      getDashboardNotices(),
      getExpirationScheduleSummary(),
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

    if (noticesResult.status === "fulfilled") {
      setDashboardNotices(Array.isArray(noticesResult.value) ? noticesResult.value : []);
    } else {
      setDashboardNotices([]);
    }

    if (expirationResult.status === "fulfilled") {
      setExpirationSummary({ ...EMPTY_EXPIRATION_SUMMARY, ...(expirationResult.value || {}) });
    } else {
      setExpirationSummary(EMPTY_EXPIRATION_SUMMARY);
    }

    setDashboardState({
      isLoading: false,
      error: getDashboardError([
        assetResult,
        softwareResult,
        vehicleResult,
        networkResult,
        recentLogResult,
        noticesResult,
        expirationResult,
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

  const displayedNotices = useMemo(
    () => sortItems(dashboardNotices, noticeSortValue, {
      created: ["created_at"],
      updated: ["updated_at", "created_at"],
      title: ["title"],
    }).slice(0, 5),
    [dashboardNotices, noticeSortValue],
  );

  const displayedRecentLogs = useMemo(
    () => recentLogs.slice(0, 6),
    [recentLogs],
  );

  const recentInsuranceLogs = useMemo(
    () => recentLogs.filter(isVehicleInsuranceLog).slice(0, 4),
    [recentLogs],
  );

  const openNoticeForm = (notice = null) => {
    setNoticeFormState({
      error: "",
      isOpen: true,
      isSubmitting: false,
      notice,
    });
  };

  const closeNoticeForm = () => {
    setNoticeFormState({ error: "", isOpen: false, isSubmitting: false, notice: null });
  };

  const handleNoticeSubmit = async (payload) => {
    setNoticeFormState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      if (noticeFormState.notice) {
        await updateDashboardNotice(noticeFormState.notice.id, payload);
      } else {
        await createDashboardNotice(payload);
      }
      setNoticeAdminUnlocked(true);
      closeNoticeForm();
      await loadDashboard();
    } catch (error) {
      setNoticeFormState((current) => ({
        ...current,
        error: error.message,
        isSubmitting: false,
      }));
    }
  };

  const openNoticeDelete = (notice) => {
    setNoticeDeleteState({
      adminPassword: "",
      error: "",
      isOpen: true,
      isSubmitting: false,
      notice,
    });
  };

  const closeNoticeDelete = () => {
    setNoticeDeleteState({
      adminPassword: "",
      error: "",
      isOpen: false,
      isSubmitting: false,
      notice: null,
    });
  };

  const handleNoticeDelete = async () => {
    if (!noticeDeleteState.notice) {
      return;
    }
    setNoticeDeleteState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      await deleteDashboardNotice(noticeDeleteState.notice.id, noticeDeleteState.adminPassword);
      setNoticeAdminUnlocked(true);
      closeNoticeDelete();
      setNoticeDetail(null);
      await loadDashboard();
    } catch (error) {
      setNoticeDeleteState((current) => ({
        ...current,
        error: error.message,
        isSubmitting: false,
      }));
    }
  };

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
        title: "점검·만료",
        tone: expirationSummary.overdue_count ? "red" : expirationSummary.within_7_days_count ? "amber" : "green",
        action: "expiration_schedules",
        rows: [
          ["기한 초과", expirationSummary.overdue_count],
          ["7일 이내", expirationSummary.within_7_days_count],
          ["30일 이내", expirationSummary.within_30_days_count],
          ["정상", expirationSummary.normal_count],
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
    [assetSummary, expirationSummary, networkStatus, softwareSummary, vehicleSummary],
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
            <h3>공지사항</h3>
            <div className="dashboard-panel-actions">
              <SortSelect
                value={noticeSortValue}
                options={BOARD_SORT_OPTIONS}
                onChange={setNoticeSortValue}
              />
              <button type="button" className="link-button" onClick={() => openNoticeForm()}>
                새 공지
              </button>
            </div>
          </div>

          {dashboardState.isLoading ? (
            <div className="dashboard-empty dashboard-notice-empty">공지사항을 불러오는 중입니다.</div>
          ) : displayedNotices.length === 0 ? (
            <div className="dashboard-empty dashboard-notice-empty">등록된 공지사항이 없습니다.</div>
          ) : (
            <ul className="dashboard-notice-list">
              {displayedNotices.map((notice) => (
                <li key={notice.id}>
                  <button type="button" className="dashboard-notice-item" onClick={() => setNoticeDetail(notice)}>
                    <span className={`dashboard-notice-badge dashboard-notice-badge-${getNoticeTone(notice.notice_type)}`}>
                      {formatText(notice.notice_type)}
                    </span>
                    <div className="dashboard-notice-main">
                      <div className="dashboard-notice-title-row">
                        <strong title={formatText(notice.title)}>
                          {notice.is_pinned ? "[고정] " : ""}{formatText(notice.title)}
                        </strong>
                        <span>{formatDate(notice.created_at)}</span>
                      </div>
                    </div>
                  </button>
                  {noticeAdminUnlocked ? (
                    <div className="dashboard-notice-actions">
                      <button type="button" className="link-button" onClick={() => openNoticeForm(notice)}>
                        수정
                      </button>
                      <button type="button" className="link-button danger-link-button" onClick={() => openNoticeDelete(notice)}>
                        삭제
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dashboard-panel dashboard-expiration-panel">
          <div className="dashboard-panel-heading">
            <h3>점검·만료 현황</h3>
            <button type="button" className="link-button" onClick={() => onNavigate?.("expiration_schedules")}>
              관리
            </button>
          </div>
          <div className="dashboard-expiration-counts">
            <span className="expiration-count-overdue">기한 초과 {formatCount(expirationSummary.overdue_count)}건</span>
            <span className="expiration-count-week">7일 이내 {formatCount(expirationSummary.within_7_days_count)}건</span>
            <span className="expiration-count-month">30일 이내 {formatCount(expirationSummary.within_30_days_count)}건</span>
          </div>
          {expirationSummary.upcoming_items.length === 0 ? (
            <div className="dashboard-empty">임박한 점검·만료 일정이 없습니다.</div>
          ) : (
            <div className="dashboard-expiration-list">
              {expirationSummary.upcoming_items.map((item) => (
                <button
                  type="button"
                  className={`dashboard-expiration-item dashboard-expiration-${item.status}`}
                  key={item.id}
                  onClick={() => {
                    openExpirationScheduleFilter(item.status);
                    onNavigate?.("expiration_schedules");
                  }}
                >
                  <strong>{getCategoryLabel(item.category)} · {item.target_name}</strong>
                  <span>{formatDaysLeft(item)}</span>
                </button>
              ))}
            </div>
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

      <DashboardNoticeFormModal
        error={noticeFormState.error}
        isOpen={noticeFormState.isOpen}
        isSubmitting={noticeFormState.isSubmitting}
        notice={noticeFormState.notice}
        onClose={closeNoticeForm}
        onSubmit={handleNoticeSubmit}
      />
      <DashboardNoticeDetailModal
        canManage={noticeAdminUnlocked}
        notice={noticeDetail}
        onClose={() => setNoticeDetail(null)}
        onDelete={(notice) => {
          setNoticeDetail(null);
          openNoticeDelete(notice);
        }}
        onEdit={(notice) => {
          setNoticeDetail(null);
          openNoticeForm(notice);
        }}
      />
      <DashboardNoticeDeleteModal
        state={noticeDeleteState}
        onChangePassword={(adminPassword) =>
          setNoticeDeleteState((current) => ({ ...current, adminPassword }))
        }
        onClose={closeNoticeDelete}
        onConfirm={handleNoticeDelete}
      />
    </section>
  );
}

function DashboardNoticeFormModal({
  error = "",
  isOpen,
  isSubmitting = false,
  notice,
  onClose,
  onSubmit,
}) {
  const [form, setForm] = useState(EMPTY_NOTICE_FORM);

  useEffect(() => {
    if (!isOpen) {
      setForm(EMPTY_NOTICE_FORM);
      return;
    }
    setForm({
      notice_type: notice?.notice_type || "공지",
      title: notice?.title || "",
      content: notice?.content || "",
      is_pinned: Boolean(notice?.is_pinned),
      admin_password: "",
    });
  }, [isOpen, notice]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(form);
  };

  return (
    <div className="dashboard-notice-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="dashboard-notice-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-notice-form-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="dashboard-notice-modal-heading">
            <div>
              <h3 id="dashboard-notice-form-title">{notice ? "공지 수정" : "새 공지"}</h3>
              <p>대시보드에 표시할 공지사항을 작성합니다.</p>
            </div>
            <button type="button" className="icon-button" onClick={onClose} aria-label="닫기">
              x
            </button>
          </div>

          <div className="dashboard-notice-form-grid">
            <label className="field">
              <span>유형</span>
              <select
                value={form.notice_type}
                onChange={(event) => setForm((current) => ({ ...current, notice_type: event.target.value }))}
                disabled={isSubmitting}
              >
                {NOTICE_TYPES.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </label>
            <label className="field dashboard-notice-pin-field">
              <span>고정</span>
              <label className="dashboard-notice-checkbox">
                <input
                  type="checkbox"
                  checked={form.is_pinned}
                  onChange={(event) => setForm((current) => ({ ...current, is_pinned: event.target.checked }))}
                  disabled={isSubmitting}
                />
                <span>상단 표시</span>
              </label>
            </label>
            <label className="field dashboard-notice-wide-field">
              <span>제목</span>
              <input
                value={form.title}
                maxLength={200}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                disabled={isSubmitting}
              />
            </label>
            <label className="field dashboard-notice-wide-field">
              <span>내용</span>
              <textarea
                value={form.content}
                rows={5}
                maxLength={5000}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
                disabled={isSubmitting}
              />
            </label>
            <label className="field dashboard-notice-wide-field">
              <span>관리자 비밀번호</span>
              <input
                type="password"
                value={form.admin_password}
                autoComplete="current-password"
                onChange={(event) => setForm((current) => ({ ...current, admin_password: event.target.value }))}
                disabled={isSubmitting}
              />
            </label>
          </div>

          {error ? <p className="dashboard-notice-error">{error}</p> : null}

          <div className="dashboard-notice-modal-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={isSubmitting}>
              취소
            </button>
            <button
              type="submit"
              className="primary-button"
              disabled={isSubmitting || !form.title.trim() || !form.content.trim() || !form.admin_password}
            >
              {isSubmitting ? "저장 중" : "저장"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function DashboardNoticeDetailModal({ canManage, notice, onClose, onDelete, onEdit }) {
  if (!notice) {
    return null;
  }

  return (
    <div className="dashboard-notice-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="dashboard-notice-modal dashboard-notice-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-notice-detail-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dashboard-notice-modal-heading">
          <div>
            <span className={`dashboard-notice-badge dashboard-notice-badge-${getNoticeTone(notice.notice_type)}`}>
              {formatText(notice.notice_type)}
            </span>
            <h3 id="dashboard-notice-detail-title">{formatText(notice.title)}</h3>
            <p>{formatDateTime(notice.created_at)}</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="닫기">
            x
          </button>
        </div>

        <div className="dashboard-notice-detail-content">{formatText(notice.content)}</div>

        <div className="dashboard-notice-modal-actions">
          {canManage ? (
            <>
              <button type="button" className="secondary-button" onClick={() => onEdit?.(notice)}>
                수정
              </button>
              <button type="button" className="danger-button" onClick={() => onDelete?.(notice)}>
                삭제
              </button>
            </>
          ) : null}
          <button type="button" className="secondary-button" onClick={onClose}>
            닫기
          </button>
        </div>
      </section>
    </div>
  );
}

function DashboardNoticeDeleteModal({ state, onChangePassword, onClose, onConfirm }) {
  if (!state.isOpen || !state.notice) {
    return null;
  }

  return (
    <div className="dashboard-notice-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="dashboard-notice-modal dashboard-notice-delete-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-notice-delete-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dashboard-notice-modal-heading">
          <div>
            <h3 id="dashboard-notice-delete-title">공지 삭제</h3>
            <p>{formatText(state.notice.title)} 공지를 삭제합니다.</p>
          </div>
        </div>
        <label className="field">
          <span>관리자 비밀번호</span>
          <input
            type="password"
            value={state.adminPassword}
            autoComplete="current-password"
            onChange={(event) => onChangePassword?.(event.target.value)}
            disabled={state.isSubmitting}
          />
        </label>
        {state.error ? <p className="dashboard-notice-error">{state.error}</p> : null}
        <div className="dashboard-notice-modal-actions">
          <button type="button" className="secondary-button" onClick={onClose} disabled={state.isSubmitting}>
            취소
          </button>
          <button
            type="button"
            className="danger-button"
            onClick={onConfirm}
            disabled={state.isSubmitting || !state.adminPassword}
          >
            {state.isSubmitting ? "삭제 중" : "삭제"}
          </button>
        </div>
      </section>
    </div>
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

function getNoticeTone(noticeType) {
  if (noticeType === "업데이트") {
    return "update";
  }
  if (noticeType === "점검") {
    return "maintenance";
  }
  if (noticeType === "기타") {
    return "etc";
  }
  return "notice";
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

function formatDate(value) {
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
