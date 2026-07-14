import React, { useCallback, useEffect, useState } from "react";
import { getLoginAccessLogs } from "../api/client.js";
import MenuAccessLogTab from "./MenuAccessLogTab.jsx";


const EMPTY_FILTERS = {
  keyword: "", recordType: "", accessType: "", period: "", startDate: "", endDate: "",
};


export default function LoginAccessLogTab() {
  const [activeTab, setActiveTab] = useState("login");
  return (
    <section className="login-access-log-tab">
      <div className="access-log-subtabs" role="tablist" aria-label="접속기록 구분">
        <button type="button" role="tab" aria-selected={activeTab === "login"} className={activeTab === "login" ? "is-active" : ""} onClick={() => setActiveTab("login")}>로그인 기록</button>
        <button type="button" role="tab" aria-selected={activeTab === "menu"} className={activeTab === "menu" ? "is-active" : ""} onClick={() => setActiveTab("menu")}>메뉴 접근 기록</button>
      </div>
      {activeTab === "login" ? <LoginRecordPanel /> : <MenuAccessLogTab />}
    </section>
  );
}


function LoginRecordPanel() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ items: [], total: 0, totalPages: 1, loading: true, error: "" });

  const loadLogs = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      const query = buildAccessLogQuery(appliedFilters, page);
      const result = await getLoginAccessLogs(query);
      setState({
        items: Array.isArray(result?.items) ? result.items : [],
        total: Number(result?.total || 0),
        totalPages: Math.max(1, Number(result?.total_pages || 1)),
        loading: false,
        error: "",
      });
    } catch (error) {
      setState((value) => ({ ...value, loading: false, error: error?.message || "접속기록을 불러오지 못했습니다." }));
    }
  }, [appliedFilters, page]);

  useEffect(() => { loadLogs(); }, [loadLogs]);

  const applyFilters = (event) => {
    event?.preventDefault();
    setPage(1);
    setAppliedFilters({ ...filters, keyword: filters.keyword.trim() });
  };

  const applyQuickFilter = (field, value) => {
    const next = { ...filters, [field]: filters[field] === value ? "" : value };
    if (field === "period") {
      next.startDate = "";
      next.endDate = "";
    }
    setFilters(next);
    setAppliedFilters(next);
    setPage(1);
  };

  const resetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  return (
    <section className="login-access-log-panel">
      <form className="access-log-filter-panel" onSubmit={applyFilters}>
        <div className="access-log-filter-row">
          <input value={filters.keyword} onChange={(event) => setFilters((value) => ({ ...value, keyword: event.target.value }))} placeholder="사용자 ID, 이름, IP 검색" aria-label="접속기록 사용자 검색" />
          <label><span>시작일</span><input type="date" value={filters.startDate} max={filters.endDate || undefined} onChange={(event) => setFilters((value) => ({ ...value, period: "custom", startDate: event.target.value }))} /></label>
          <label><span>종료일</span><input type="date" value={filters.endDate} min={filters.startDate || undefined} onChange={(event) => setFilters((value) => ({ ...value, period: "custom", endDate: event.target.value }))} /></label>
          <button type="submit">조회</button>
          <button type="button" onClick={resetFilters}>초기화</button>
        </div>
        <div className="access-log-quick-filters" aria-label="접속기록 빠른 필터">
          <span>기간</span>
          {[['today', '오늘'], ['last7', '최근 7일'], ['last30', '최근 30일']].map(([value, label]) => <button type="button" key={value} className={filters.period === value ? "is-active" : ""} onClick={() => applyQuickFilter("period", value)}>{label}</button>)}
          <span>상태</span>
          {[['login_success', '로그인 성공'], ['login_failure', '로그인 실패'], ['logout', '로그아웃']].map(([value, label]) => <button type="button" key={value} className={filters.recordType === value ? "is-active" : ""} onClick={() => applyQuickFilter("recordType", value)}>{label}</button>)}
          <span>접속 위치</span>
          {[['internal', '내부망'], ['external', '외부망']].map(([value, label]) => <button type="button" key={value} className={filters.accessType === value ? "is-active" : ""} onClick={() => applyQuickFilter("accessType", value)}>{label}</button>)}
        </div>
      </form>

      {state.error ? <p className="user-management-error">{state.error}</p> : null}
      <div className="access-log-table-summary">총 {state.total.toLocaleString("ko-KR")}건</div>
      <div className="access-log-table-wrap">
        <table className="access-log-table">
          <thead><tr><th>상태</th><th>구분</th><th>사용자 ID</th><th>사용자 이름</th><th>접속 IP</th><th>접속 위치</th><th>브라우저</th><th>운영체제</th><th>접속 일시</th><th>실패 사유</th></tr></thead>
          <tbody>
            {state.loading ? <tr><td colSpan="10">불러오는 중...</td></tr> : null}
            {!state.loading && state.items.length === 0 ? <tr className="access-log-empty-row"><td colSpan="10">조회된 접속기록이 없습니다.</td></tr> : null}
            {!state.loading && state.items.map((item) => <tr key={item.id}>
              <td><AccessStatusBadge item={item} /></td>
              <td>{item.event_type === "logout" ? "로그아웃" : "로그인"}</td>
              <td>{item.username || "-"}</td>
              <td>{item.user_name || "-"}</td>
              <td>{item.ip_address || "-"}</td>
              <td><span className={`access-type-badge is-${item.access_type}`}>{item.access_type === "internal" ? "내부망" : "외부망"}</span></td>
              <td title={item.user_agent || ""}>{item.browser || "-"}</td>
              <td>{item.operating_system || "-"}</td>
              <td>{formatAccessDate(item.occurred_at)}</td>
              <td className="access-log-failure-reason">{item.failure_reason || "-"}</td>
            </tr>)}
          </tbody>
        </table>
      </div>
      <div className="access-log-pagination">
        <button type="button" disabled={page <= 1 || state.loading} onClick={() => setPage((value) => Math.max(1, value - 1))}>이전</button>
        <span>{page} / {state.totalPages}</span>
        <button type="button" disabled={page >= state.totalPages || state.loading} onClick={() => setPage((value) => Math.min(state.totalPages, value + 1))}>다음</button>
      </div>
    </section>
  );
}


function AccessStatusBadge({ item }) {
  if (item.event_type === "logout") return <span className="access-status-badge is-logout">로그아웃</span>;
  if (item.login_result === "failure") return <span className="access-status-badge is-failure">실패</span>;
  return <span className="access-status-badge is-success">성공</span>;
}


function buildAccessLogQuery(filters, page) {
  const query = { keyword: filters.keyword, page, page_size: 50 };
  if (filters.recordType === "login_success") Object.assign(query, { event_type: "login", login_result: "success" });
  if (filters.recordType === "login_failure") Object.assign(query, { event_type: "login", login_result: "failure" });
  if (filters.recordType === "logout") Object.assign(query, { event_type: "logout", login_result: "success" });
  if (filters.accessType) query.access_type = filters.accessType;
  const range = resolveDateRange(filters);
  if (range.start) query.start_date = range.start;
  if (range.end) query.end_date = range.end;
  return query;
}


function resolveDateRange(filters) {
  if (filters.period === "custom") return { start: filters.startDate, end: filters.endDate };
  if (!filters.period) return { start: "", end: "" };
  const end = new Date();
  const start = new Date();
  if (filters.period === "last7") start.setDate(start.getDate() - 6);
  if (filters.period === "last30") start.setDate(start.getDate() - 29);
  return { start: toDateKey(start), end: toDateKey(end) };
}


function toDateKey(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}


function formatAccessDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "-";
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}
