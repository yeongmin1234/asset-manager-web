import React, { useCallback, useEffect, useState } from "react";
import { getMenuAccessLogs } from "../api/client.js";


const EMPTY_FILTERS = { keyword: "", username: "", menuKey: "", accessType: "", period: "", startDate: "", endDate: "" };
export default function MenuAccessLogTab() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ items: [], menuOptions: [], total: 0, totalPages: 1, loading: true, error: "" });

  const loadLogs = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const result = await getMenuAccessLogs(buildQuery(appliedFilters, page));
      setState({ items: Array.isArray(result?.items) ? result.items : [], menuOptions: Array.isArray(result?.menu_options) ? result.menu_options : [], total: Number(result?.total || 0), totalPages: Math.max(1, Number(result?.total_pages || 1)), loading: false, error: "" });
    } catch (error) {
      setState((value) => ({ ...value, loading: false, error: error?.message || "메뉴 접근 기록을 불러오지 못했습니다." }));
    }
  }, [appliedFilters, page]);

  useEffect(() => { loadLogs(); }, [loadLogs]);

  const apply = (event) => {
    event.preventDefault();
    setPage(1);
    setAppliedFilters({ ...filters, keyword: filters.keyword.trim(), username: filters.username.trim() });
  };
  const quick = (field, value) => {
    const next = { ...filters, [field]: filters[field] === value ? "" : value };
    if (field === "period") Object.assign(next, { startDate: "", endDate: "" });
    setFilters(next); setAppliedFilters(next); setPage(1);
  };
  const reset = () => { setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS); setPage(1); };

  return (
    <section className="menu-access-log-panel">
      <form className="access-log-filter-panel" onSubmit={apply}>
        <div className="access-log-filter-row menu-access-log-filter-row">
          <input value={filters.username} onChange={(event) => setFilters((value) => ({ ...value, username: event.target.value }))} placeholder="사용자 ID 또는 이름" aria-label="메뉴 접근 사용자 검색" />
          <input value={filters.keyword} onChange={(event) => setFilters((value) => ({ ...value, keyword: event.target.value }))} placeholder="IP 또는 경로 검색" aria-label="메뉴 접근 IP 검색" />
          <select value={filters.menuKey} onChange={(event) => setFilters((value) => ({ ...value, menuKey: event.target.value }))} aria-label="메뉴 선택"><option value="">전체 메뉴</option>{state.menuOptions.map((option) => <option key={option.menu_key} value={option.menu_key}>{option.menu_name}</option>)}</select>
          <label><span>시작일</span><input type="date" value={filters.startDate} max={filters.endDate || undefined} onChange={(event) => setFilters((value) => ({ ...value, period: "custom", startDate: event.target.value }))} /></label>
          <label><span>종료일</span><input type="date" value={filters.endDate} min={filters.startDate || undefined} onChange={(event) => setFilters((value) => ({ ...value, period: "custom", endDate: event.target.value }))} /></label>
          <button type="submit">조회</button><button type="button" onClick={reset}>초기화</button>
        </div>
        <div className="access-log-quick-filters">
          <span>기간</span>{[["today", "오늘"], ["last7", "최근 7일"], ["last30", "최근 30일"]].map(([value, label]) => <button type="button" key={value} className={filters.period === value ? "is-active" : ""} onClick={() => quick("period", value)}>{label}</button>)}
          <span>접속 위치</span>{[["internal", "내부망"], ["external", "외부망"]].map(([value, label]) => <button type="button" key={value} className={filters.accessType === value ? "is-active" : ""} onClick={() => quick("accessType", value)}>{label}</button>)}
        </div>
      </form>
      {state.error ? <p className="user-management-error">{state.error}</p> : null}
      <div className="access-log-table-summary">총 {state.total.toLocaleString("ko-KR")}건</div>
      <div className="access-log-table-wrap"><table className="access-log-table menu-access-log-table">
        <thead><tr><th>사용자 ID</th><th>사용자 이름</th><th>메뉴</th><th>경로</th><th>접속 IP</th><th>접속 구분</th><th>브라우저</th><th>운영체제</th><th>접속 일시</th></tr></thead>
        <tbody>
          {state.loading ? <tr><td colSpan="9">불러오는 중...</td></tr> : null}
          {!state.loading && state.items.length === 0 ? <tr className="access-log-empty-row"><td colSpan="9">조회된 메뉴 접근 기록이 없습니다.</td></tr> : null}
          {!state.loading && state.items.map((item) => <tr key={item.id}><td>{item.username}</td><td>{item.user_name || "-"}</td><td>{item.menu_name}</td><td title={item.route_path}>{item.route_path}</td><td>{item.ip_address || "-"}</td><td><span className={`access-type-badge is-${item.access_type}`}>{item.access_type === "internal" ? "내부망" : "외부망"}</span></td><td title={item.user_agent || ""}>{item.browser || "-"}</td><td>{item.operating_system || "-"}</td><td>{formatDate(item.occurred_at)}</td></tr>)}
        </tbody>
      </table></div>
      <div className="access-log-pagination"><button type="button" disabled={page <= 1 || state.loading} onClick={() => setPage((value) => Math.max(1, value - 1))}>이전</button><span>{page} / {state.totalPages}</span><button type="button" disabled={page >= state.totalPages || state.loading} onClick={() => setPage((value) => Math.min(state.totalPages, value + 1))}>다음</button></div>
    </section>
  );
}


function buildQuery(filters, page) {
  const query = { keyword: filters.keyword, username: filters.username, page, page_size: 50 };
  if (filters.menuKey) query.menu_key = filters.menuKey;
  if (filters.accessType) query.access_type = filters.accessType;
  const range = resolveRange(filters); if (range.start) query.start_date = range.start; if (range.end) query.end_date = range.end;
  return query;
}

function resolveRange(filters) {
  if (filters.period === "custom") return { start: filters.startDate, end: filters.endDate };
  if (!filters.period) return { start: "", end: "" };
  const end = new Date(); const start = new Date();
  if (filters.period === "last7") start.setDate(start.getDate() - 6);
  if (filters.period === "last30") start.setDate(start.getDate() - 29);
  return { start: dateKey(start), end: dateKey(end) };
}

function dateKey(date) { const pad = (value) => String(value).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`; }
function formatDate(value) { const date = new Date(value); if (Number.isNaN(date.getTime())) return value || "-"; const pad = (part) => String(part).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`; }
