import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  completeExpirationSchedule,
  createExpirationSchedule,
  deleteExpirationSchedule,
  getExpirationScheduleSummary,
  getExpirationSchedules,
  updateExpirationSchedule,
} from "../api/client.js";
import AttachmentPanel from "./AttachmentPanel.jsx";

const CATEGORY_OPTIONS = [
  ["vehicle_insurance", "차량보험"],
  ["vehicle_inspection", "차량검사"],
  ["fire_insurance", "화재보험"],
  ["contract", "계약"],
  ["rental", "렌탈"],
  ["software_license", "SW 라이선스"],
  ["warranty", "보증기간"],
  ["server_maintenance", "서버 점검"],
  ["nas_maintenance", "NAS 점검"],
  ["other", "기타"],
];

const STATUS_OPTIONS = [
  ["", "전체"],
  ["overdue", "기한 초과"],
  ["within_7_days", "7일 이내"],
  ["within_30_days", "30일 이내"],
  ["normal", "정상"],
  ["completed", "완료"],
];

const EMPTY_FORM = {
  category: "vehicle_inspection",
  title: "",
  target_name: "",
  due_date: "",
  notification_days: 30,
  memo: "",
  source_type: "",
  source_id: "",
  is_completed: false,
};

const EMPTY_SUMMARY = {
  overdue_count: 0,
  within_7_days_count: 0,
  within_30_days_count: 0,
  normal_count: 0,
  completed_count: 0,
  upcoming_items: [],
};
const FILTER_STORAGE_KEY = "assetManager.expirationFilters";

function ExpirationSchedulePage({ currentUser }) {
  const isAdmin = currentUser?.role === "admin";
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [summaryAvailable, setSummaryAvailable] = useState(false);
  const [filters, setFilters] = useState(() => getInitialFilters());
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [attachmentTarget, setAttachmentTarget] = useState(null);
  const [state, setState] = useState({ error: "", isLoading: true, message: "", savingId: null });

  const loadData = useCallback(async () => {
    setState((current) => ({ ...current, error: "", isLoading: true }));
    const query = {
      status: filters.status,
      category: filters.category,
      keyword: filters.keyword.trim(),
    };
    const [itemsResult, summaryResult] = await Promise.allSettled([
      getExpirationSchedules(query),
      getExpirationScheduleSummary(),
    ]);
    const errors = [];

    if (itemsResult.status === "fulfilled") {
      setItems(Array.isArray(itemsResult.value) ? itemsResult.value : []);
    } else {
      setItems([]);
      errors.push(`목록: ${formatApiError(itemsResult.reason)}`);
    }

    if (summaryResult.status === "fulfilled") {
      setSummary({ ...EMPTY_SUMMARY, ...(summaryResult.value || {}) });
      setSummaryAvailable(true);
    } else {
      setSummaryAvailable(false);
      errors.push(`요약: ${formatApiError(summaryResult.reason)}`);
    }

    setState((current) => ({ ...current, error: errors.join(" / "), isLoading: false }));
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const summaryCards = useMemo(
    () => [
      ["기한 초과", summary.overdue_count, "overdue"],
      ["7일 이내", summary.within_7_days_count, "within_7_days"],
      ["30일 이내", summary.within_30_days_count, "within_30_days"],
      ["정상", summary.normal_count, "normal"],
    ],
    [summary],
  );

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!isAdmin) {
      return;
    }
    setState((current) => ({ ...current, error: "", message: "", savingId: editingId || "create" }));
    try {
      const payload = buildPayload(form);
      if (editingId) {
        await updateExpirationSchedule(editingId, payload);
      } else {
        await createExpirationSchedule(payload);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
      setState((current) => ({
        ...current,
        message: editingId ? "일정을 수정했습니다." : "일정을 등록했습니다.",
        savingId: null,
      }));
      await loadData();
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, savingId: null }));
    }
  };

  const handleEdit = (item) => {
    setEditingId(item.id);
    setForm({
      category: item.category || "other",
      title: item.title || "",
      target_name: item.target_name || "",
      due_date: item.due_date || "",
      notification_days: item.notification_days ?? 30,
      memo: item.memo || "",
      source_type: item.source_type || "",
      source_id: item.source_id || "",
      is_completed: Boolean(item.is_completed),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleComplete = async (item) => {
    setState((current) => ({ ...current, error: "", message: "", savingId: item.id }));
    try {
      await completeExpirationSchedule(item.id, !item.is_completed);
      setState((current) => ({
        ...current,
        message: item.is_completed ? "완료를 취소했습니다." : "일정을 완료 처리했습니다.",
        savingId: null,
      }));
      await loadData();
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, savingId: null }));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    setState((current) => ({ ...current, error: "", message: "", savingId: deleteTarget.id }));
    try {
      await deleteExpirationSchedule(deleteTarget.id);
      setItems((current) => current.filter((item) => item.id !== deleteTarget.id));
      setDeleteTarget(null);
      setState((current) => ({
        ...current,
        message: "일정을 완전히 삭제했습니다.",
        savingId: null,
      }));
      await loadData();
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, savingId: null }));
    }
  };

  return (
    <section className="expiration-page">
      <div className="portal-screen-heading expiration-heading">
        <div>
          <h2>점검·만료 관리</h2>
          <p>차량검사, 보험, 계약, 라이선스, 보증기간과 서버 점검 일정을 통합 관리합니다.</p>
        </div>
      </div>

      <section className="expiration-summary-grid" aria-label="점검·만료 요약">
        {summaryCards.map(([label, value, status]) => (
          <button
            type="button"
            className={`expiration-summary-card expiration-summary-${status}`}
            key={status}
            onClick={() => setFilters((current) => ({ ...current, status }))}
          >
            <span>{label}</span>
            <strong>{summaryAvailable ? Number(value || 0).toLocaleString("ko-KR") : "—"}</strong>
          </button>
        ))}
      </section>

      {isAdmin ? (
        <form className="expiration-form" onSubmit={handleSubmit}>
          <div className="expiration-form-heading">
            <h3>{editingId ? "일정 수정" : "빠른 등록"}</h3>
            {editingId ? (
              <button type="button" className="link-button" onClick={() => {
                setEditingId(null);
                setForm(EMPTY_FORM);
              }}>
                수정 취소
              </button>
            ) : null}
          </div>
          <select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
            {CATEGORY_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
          <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="제목" required />
          <input value={form.target_name} onChange={(event) => setForm({ ...form, target_name: event.target.value })} placeholder="대상" required />
          <input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} required />
          <input type="number" min="0" max="3650" value={form.notification_days} onChange={(event) => setForm({ ...form, notification_days: event.target.value })} aria-label="사전 알림 일수" />
          <input className="expiration-form-memo" value={form.memo} onChange={(event) => setForm({ ...form, memo: event.target.value })} placeholder="비고" />
          <button type="submit" className="primary-action" disabled={state.savingId !== null}>
            {state.savingId ? "저장 중..." : editingId ? "저장" : "등록"}
          </button>
        </form>
      ) : null}

      <section className="expiration-filter-bar" aria-label="일정 검색 및 필터">
        <div className="expiration-status-tabs">
          {STATUS_OPTIONS.map(([value, label]) => (
            <button
              type="button"
              className={filters.status === value ? "active" : ""}
              key={value || "all"}
              onClick={() => setFilters((current) => ({ ...current, status: value }))}
            >
              {label}
            </button>
          ))}
        </div>
        <select value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
          <option value="">전체 구분</option>
          {CATEGORY_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
        </select>
        <input value={filters.keyword} onChange={(event) => setFilters({ ...filters, keyword: event.target.value })} placeholder="제목, 대상, 비고 검색" />
      </section>

      {state.message ? <p className="expiration-message">{state.message}</p> : null}
      {state.error ? <p className="expiration-error">{state.error}</p> : null}

      <div className="expiration-table-wrap">
        <table className="expiration-table">
          <thead>
            <tr>
              <th>상태</th>
              <th>구분</th>
              <th className="expiration-left-heading">제목</th>
              <th className="expiration-left-heading">대상</th>
              <th>만료/점검일</th>
              <th>남은 기간</th>
              <th className="expiration-left-heading">비고</th>
              <th>관리</th>
            </tr>
          </thead>
          <tbody>
            {state.isLoading ? (
              <tr><td colSpan="8">불러오는 중...</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan="8">등록된 일정이 없습니다.</td></tr>
            ) : items.map((item) => (
              <tr key={item.id}>
                <td><StatusBadge status={item.status} /></td>
                <td>{getCategoryLabel(item.category)}</td>
                <td className="expiration-text-cell">{item.title}</td>
                <td className="expiration-text-cell">{item.target_name}</td>
                <td>{formatDate(item.due_date)}</td>
                <td>{formatDaysLeft(item)}</td>
                <td className="expiration-text-cell">{item.memo || "-"}</td>
                <td>
                  {isAdmin ? (
                    <div className="expiration-row-actions">
                      <button type="button" className="link-button" onClick={() => handleEdit(item)}>수정</button>
                      <button type="button" className="link-button" onClick={() => setAttachmentTarget(item)}>첨부</button>
                      <button type="button" className="link-button" onClick={() => handleComplete(item)}>
                        {item.is_completed ? "완료 취소" : "완료"}
                      </button>
                      <button type="button" className="link-button danger-link-button" onClick={() => setDeleteTarget(item)}>삭제</button>
                    </div>
                  ) : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {deleteTarget ? (
        <div className="expiration-delete-backdrop" role="presentation" onMouseDown={() => setDeleteTarget(null)}>
          <section className="expiration-delete-modal" role="alertdialog" aria-modal="true" aria-labelledby="expiration-delete-title" onMouseDown={(event) => event.stopPropagation()}>
            <h3 id="expiration-delete-title">일정 완전 삭제</h3>
            <p>{deleteTarget.title} 일정을 완전히 삭제하시겠습니까?</p>
            <div className="expiration-delete-actions">
              <button type="button" className="secondary-button" onClick={() => setDeleteTarget(null)}>취소</button>
              <button type="button" className="danger-button" onClick={handleDelete} disabled={state.savingId !== null}>삭제</button>
            </div>
          </section>
        </div>
      ) : null}
      {attachmentTarget ? (
        <div className="expiration-delete-backdrop" role="presentation" onMouseDown={() => setAttachmentTarget(null)}>
          <section className="expiration-delete-modal expiration-attachment-modal" role="dialog" aria-modal="true" aria-labelledby="expiration-attachment-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="expiration-form-heading">
              <h3 id="expiration-attachment-title">{attachmentTarget.title} 첨부파일</h3>
              <button type="button" className="secondary-button" onClick={() => setAttachmentTarget(null)}>닫기</button>
            </div>
            <AttachmentPanel
              canManage={isAdmin}
              entityId={attachmentTarget.id}
              entityType="expiration_schedule"
              title="첨부파일"
            />
          </section>
        </div>
      ) : null}
    </section>
  );
}

function StatusBadge({ status }) {
  return <span className={`expiration-status-badge expiration-status-${status}`}>{getStatusLabel(status)}</span>;
}

function buildPayload(form) {
  return {
    category: form.category,
    title: form.title.trim(),
    target_name: form.target_name.trim(),
    due_date: form.due_date,
    notification_days: Number(form.notification_days || 0),
    memo: form.memo.trim() || null,
    source_type: form.source_type.trim() || null,
    source_id: form.source_id ? Number(form.source_id) : null,
    is_completed: Boolean(form.is_completed),
  };
}

function getCategoryLabel(category) {
  return CATEGORY_OPTIONS.find(([value]) => value === category)?.[1] || category || "-";
}

function getStatusLabel(status) {
  const labels = {
    overdue: "기한 초과",
    within_7_days: "7일 이내",
    within_30_days: "30일 이내",
    normal: "정상",
    completed: "완료",
  };
  return labels[status] || "-";
}

function formatDaysLeft(item) {
  if (item.is_completed || item.status === "completed") {
    return "완료";
  }
  const daysLeft = Number(item.days_left);
  if (!Number.isFinite(daysLeft)) {
    return "-";
  }
  if (daysLeft < 0) {
    return `${Math.abs(daysLeft)}일 초과`;
  }
  if (daysLeft === 0) {
    return "D-Day";
  }
  return `D-${daysLeft}`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleDateString("ko-KR");
}

function formatApiError(error) {
  const status = Number(error?.status);
  const prefix = [401, 403, 404, 500].includes(status) ? `HTTP ${status} ` : status ? `HTTP ${status} ` : "";
  return `${prefix}${error?.message || "API 요청에 실패했습니다."}`;
}

function getInitialFilters() {
  if (typeof window === "undefined") {
    return { status: "", category: "", keyword: "" };
  }
  try {
    const storedValue = window.sessionStorage.getItem(FILTER_STORAGE_KEY);
    window.sessionStorage.removeItem(FILTER_STORAGE_KEY);
    if (!storedValue) {
      return { status: "", category: "", keyword: "" };
    }
    const parsedValue = JSON.parse(storedValue);
    return {
      status: parsedValue?.status || "",
      category: parsedValue?.category || "",
      keyword: parsedValue?.keyword || "",
    };
  } catch {
    return { status: "", category: "", keyword: "" };
  }
}

function openExpirationScheduleFilter(status) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(
    FILTER_STORAGE_KEY,
    JSON.stringify({ status: status || "", category: "", keyword: "" }),
  );
}

export { CATEGORY_OPTIONS, formatDaysLeft, getCategoryLabel, getStatusLabel, openExpirationScheduleFilter };
export default ExpirationSchedulePage;
