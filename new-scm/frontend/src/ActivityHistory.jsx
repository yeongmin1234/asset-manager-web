import React, { useEffect, useState } from "react";
import { getActivityHistory } from "./services/activityBridge";
import { actionLabels, formatActivityTime, moduleLabels } from "./activityPresentation";

const initialFilters = { start_date: "", end_date: "", user: "", module: "", action: "", keyword: "" };

export default function ActivityHistory() {
  const [filters, setFilters] = useState(initialFilters);
  const [applied, setApplied] = useState(initialFilters);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState({ items: [], total: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getActivityHistory({ ...applied, offset, limit: 50 }).then(
      (data) => { if (active) { setResult(data); setError(""); } },
      (failure) => { if (active) setError(failure.message); },
    );
    return () => { active = false; };
  }, [applied, offset]);

  const setFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  return (
    <section className="scm-activity-history">
      <header><h1>전체 작업 이력</h1><span>미리보기 작업 기록</span></header>
      <form onSubmit={(event) => { event.preventDefault(); setOffset(0); setApplied({ ...filters }); }}>
        <label>시작일<input type="date" value={filters.start_date} onChange={(event) => setFilter("start_date", event.target.value)} /></label>
        <label>종료일<input type="date" value={filters.end_date} onChange={(event) => setFilter("end_date", event.target.value)} /></label>
        <label>사용자<input value={filters.user} onChange={(event) => setFilter("user", event.target.value)} /></label>
        <label>모듈<select value={filters.module} onChange={(event) => setFilter("module", event.target.value)}><option value="">전체</option>{Object.entries(moduleLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>작업 유형<select value={filters.action} onChange={(event) => setFilter("action", event.target.value)}><option value="">전체</option>{Object.entries(actionLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>키워드<input value={filters.keyword} onChange={(event) => setFilter("keyword", event.target.value)} /></label>
        <button type="submit">검색</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <div className="scm-activity-history__table"><table><thead><tr><th>날짜/시간</th><th>사용자</th><th>작업 내용</th><th>모듈</th><th>작업 유형</th></tr></thead><tbody>
        {result.items.length ? result.items.map((item) => <tr key={item.id}><td>{formatActivityTime(item.created_at)}</td><td>{item.user_name}</td><td>{item.message}</td><td>{moduleLabels[item.module] || item.module}</td><td>{actionLabels[item.action] || item.action}</td></tr>) : <tr><td colSpan={5}>기록된 작업이 없습니다.</td></tr>}
      </tbody></table></div>
      <footer><span>총 {result.total}건</span><button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>이전</button><button type="button" disabled={offset + 50 >= result.total} onClick={() => setOffset(offset + 50)}>다음</button></footer>
    </section>
  );
}
