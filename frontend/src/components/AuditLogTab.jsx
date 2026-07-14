import React, { useCallback, useEffect, useState } from "react";
import { getAuditLogs } from "../api/client.js";

const EMPTY = { keyword: "", username: "", menuKey: "", actionType: "", targetType: "", accessType: "", period: "", startDate: "", endDate: "" };
const ACTIONS = [["create", "등록"], ["update", "수정"], ["delete", "삭제"], ["activate", "활성화"], ["deactivate", "비활성화"], ["permission_change", "권한 변경"], ["excel_import", "엑셀 일괄등록"]];
const ACTION_LABELS = Object.fromEntries(ACTIONS);

export default function AuditLogTab() {
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ items: [], menus: [], targets: [], total: 0, pages: 1, loading: true, error: "" });
  const load = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const result = await getAuditLogs(buildQuery(applied, page));
      setState({ items: result?.items || [], menus: result?.menu_options || [], targets: result?.target_type_options || [], total: Number(result?.total || 0), pages: Math.max(1, Number(result?.total_pages || 1)), loading: false, error: "" });
    } catch (error) {
      setState((value) => ({ ...value, loading: false, error: error?.message || "감사로그를 불러오지 못했습니다." }));
    }
  }, [applied, page]);
  useEffect(() => { load(); }, [load]);
  const apply = (event) => { event.preventDefault(); setPage(1); setApplied({ ...filters, keyword: filters.keyword.trim(), username: filters.username.trim() }); };
  const reset = () => { setFilters(EMPTY); setApplied(EMPTY); setPage(1); };
  const quick = (field, value) => { const next = { ...filters, [field]: filters[field] === value ? "" : value }; if (field === "period") Object.assign(next, { startDate: "", endDate: "" }); setFilters(next); setApplied(next); setPage(1); };
  return <section className="audit-log-tab">
    <form className="access-log-filter-panel" onSubmit={apply}>
      <div className="audit-log-filter-row">
        <input value={filters.username} onChange={(e) => setFilters({ ...filters, username: e.target.value })} placeholder="사용자 ID 또는 이름" />
        <input value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} placeholder="대상, 작업 내용, IP 검색" />
        <select value={filters.menuKey} onChange={(e) => setFilters({ ...filters, menuKey: e.target.value })}><option value="">전체 메뉴</option>{state.menus.map((item) => <option key={item.menu_key} value={item.menu_key}>{item.menu_name}</option>)}</select>
        <select value={filters.actionType} onChange={(e) => setFilters({ ...filters, actionType: e.target.value })}><option value="">전체 작업</option>{ACTIONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
        <select value={filters.targetType} onChange={(e) => setFilters({ ...filters, targetType: e.target.value })}><option value="">전체 대상</option>{state.targets.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <button type="submit">조회</button><button type="button" onClick={reset}>초기화</button>
      </div>
      <div className="audit-log-filter-row audit-log-date-row">
        <label><span>시작일</span><input type="date" value={filters.startDate} max={filters.endDate || undefined} onChange={(e) => setFilters({ ...filters, period: "custom", startDate: e.target.value })} /></label>
        <label><span>종료일</span><input type="date" value={filters.endDate} min={filters.startDate || undefined} onChange={(e) => setFilters({ ...filters, period: "custom", endDate: e.target.value })} /></label>
        <div className="access-log-quick-filters"><span>기간</span>{[["today", "오늘"], ["last7", "최근 7일"], ["last30", "최근 30일"]].map(([key, label]) => <button type="button" key={key} className={filters.period === key ? "is-active" : ""} onClick={() => quick("period", key)}>{label}</button>)}<span>접속 위치</span>{[["internal", "내부망"], ["external", "외부망"]].map(([key, label]) => <button type="button" key={key} className={filters.accessType === key ? "is-active" : ""} onClick={() => quick("accessType", key)}>{label}</button>)}</div>
      </div>
    </form>
    {state.error ? <p className="user-management-error">{state.error}</p> : null}
    <div className="access-log-table-summary">총 {state.total.toLocaleString("ko-KR")}건</div>
    <div className="access-log-table-wrap"><table className="access-log-table audit-log-table"><thead><tr><th>작업 상태</th><th>작업 유형</th><th>사용자 ID</th><th>사용자 이름</th><th>메뉴</th><th>대상</th><th>작업 내용</th><th>접속 IP</th><th>접속 구분</th><th>작업 일시</th></tr></thead><tbody>
      {state.loading ? <tr><td colSpan="10">불러오는 중...</td></tr> : null}
      {!state.loading && state.items.length === 0 ? <tr className="access-log-empty-row"><td colSpan="10">조회된 감사로그가 없습니다.</td></tr> : null}
      {!state.loading && state.items.map((item) => <tr key={item.id}><td><span className={`audit-action-badge is-${item.action_type}`}>{ACTION_LABELS[item.action_type] || item.action_type}</span></td><td>{item.action_type}</td><td>{item.username}</td><td>{item.user_name}</td><td>{item.menu_name}</td><td title={`${item.target_type} #${item.target_id || "-"}`}>{item.target_name || "-"}</td><td className="audit-summary-cell" title={item.action_summary}>{item.action_summary}</td><td>{item.ip_address || "-"}</td><td><span className={`access-type-badge is-${item.access_type}`}>{item.access_type === "internal" ? "내부망" : "외부망"}</span></td><td>{formatDate(item.occurred_at)}</td></tr>)}
    </tbody></table></div>
    <div className="access-log-pagination"><button type="button" disabled={page <= 1 || state.loading} onClick={() => setPage((v) => v - 1)}>이전</button><span>{page} / {state.pages}</span><button type="button" disabled={page >= state.pages || state.loading} onClick={() => setPage((v) => v + 1)}>다음</button></div>
  </section>;
}

function buildQuery(filters, page) { const query = { keyword: filters.keyword, username: filters.username, page, page_size: 50 }; if (filters.menuKey) query.menu_key = filters.menuKey; if (filters.actionType) query.action_type = filters.actionType; if (filters.targetType) query.target_type = filters.targetType; if (filters.accessType) query.access_type = filters.accessType; const range = dateRange(filters); if (range.start) query.start_date = range.start; if (range.end) query.end_date = range.end; return query; }
function dateRange(filters) { if (filters.period === "custom") return { start: filters.startDate, end: filters.endDate }; if (!filters.period) return {}; const end = new Date(); const start = new Date(); if (filters.period === "last7") start.setDate(start.getDate() - 6); if (filters.period === "last30") start.setDate(start.getDate() - 29); return { start: key(start), end: key(end) }; }
function key(date) { const pad = (v) => String(v).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`; }
function formatDate(value) { const date = new Date(value); if (Number.isNaN(date.getTime())) return value || "-"; const pad = (v) => String(v).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`; }
