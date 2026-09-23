import useDownloadStatus from "../hooks/useDownloadStatus.js";
import React, { useCallback, useEffect, useState } from "react";
import { downloadAuditLogs, getAuditLog, getAuditLogs } from "../api/client.js";

const EMPTY = { keyword: "", username: "", menuKey: "", actionType: "", targetType: "", accessType: "", changedField: "", period: "", startDate: "", endDate: "" };
const ACTIONS = [["create", "등록"], ["update", "수정"], ["delete", "삭제"], ["activate", "활성화"], ["deactivate", "비활성화"], ["permission_change", "권한 변경"], ["excel_import", "엑셀 일괄등록"], ["export", "엑셀 다운로드"]];
const ACTION_LABELS = Object.fromEntries(ACTIONS);
const FIELD_LABELS = { department: "부서", name: "이름", dowoffice: "다우오피스", erp: "ERP", scm: "SCM", nas: "NAS", menu_permissions: "메뉴 권한", status: "상태", role: "역할", is_active: "활성 상태", title: "제목", vehicle_number: "차량번호", vehicle_name: "차량명", owner_name: "사용자", expire_date: "만료일", due_date: "예정일", category: "분류", target_name: "대상 이름", company_name: "업체명" };
const PERMISSION_LABELS = { dashboard: "대시보드", assets: "자산 관리", software: "SW 현황", company_cars: "법인차량 관리", fire_insurance: "파주화재보험", access_info: "접속정보 관리", equipment_status: "장비 현황", hr_list: "인사업무 리스트", statistics: "통계 / 리포트", changelog: "변경 이력", work_manual: "업무설명서", vendor_contacts: "업체연락처", expiration_schedules: "점검·만료 관리", drink_orders: "음료주문기록" };

export default function AuditLogTab() {
  const downloadBusy = useDownloadStatus();
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ items: [], menus: [], targets: [], total: 0, pages: 1, loading: true, error: "" });
  const [detail, setDetail] = useState({ open: false, loading: false, item: null, error: "" });
  const [downloading, setDownloading] = useState(false);
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
  const openDetail = async (id) => { setDetail({ open: true, loading: true, item: null, error: "" }); try { setDetail({ open: true, loading: false, item: await getAuditLog(id), error: "" }); } catch (error) { setDetail({ open: true, loading: false, item: null, error: error?.message || "상세 정보를 불러오지 못했습니다." }); } };
  const exportExcel = async () => { setDownloading(true); try { await downloadAuditLogs(buildQuery(applied), { onTransferError: (message) => setState((value) => ({ ...value, error: message })) }); } catch (error) { setState((value) => ({ ...value, error: error?.message || "엑셀 다운로드에 실패했습니다." })); } finally { setDownloading(false); } };
  return <section className="audit-log-tab">
    <form className="access-log-filter-panel" onSubmit={apply}>
      <div className="audit-log-filter-row">
        <input value={filters.username} onChange={(e) => setFilters({ ...filters, username: e.target.value })} placeholder="사용자 ID 또는 이름" />
        <input value={filters.keyword} onChange={(e) => setFilters({ ...filters, keyword: e.target.value })} placeholder="대상, 작업 내용, IP 검색" />
        <select value={filters.menuKey} onChange={(e) => setFilters({ ...filters, menuKey: e.target.value })}><option value="">전체 메뉴</option>{state.menus.map((item) => <option key={item.menu_key} value={item.menu_key}>{item.menu_name}</option>)}</select>
        <select value={filters.actionType} onChange={(e) => setFilters({ ...filters, actionType: e.target.value })}><option value="">전체 작업</option>{ACTIONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
        <select value={filters.targetType} onChange={(e) => setFilters({ ...filters, targetType: e.target.value })}><option value="">전체 대상</option>{state.targets.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <input value={filters.changedField} onChange={(e) => setFilters({ ...filters, changedField: e.target.value })} placeholder="변경 필드 (예: ERP)" />
        <button type="submit">조회</button><button type="button" onClick={reset}>초기화</button>
      </div>
      <div className="audit-log-filter-row audit-log-date-row">
        <label><span>시작일</span><input type="date" value={filters.startDate} max={filters.endDate || undefined} onChange={(e) => setFilters({ ...filters, period: "custom", startDate: e.target.value })} /></label>
        <label><span>종료일</span><input type="date" value={filters.endDate} min={filters.startDate || undefined} onChange={(e) => setFilters({ ...filters, period: "custom", endDate: e.target.value })} /></label>
        <div className="access-log-quick-filters"><span>기간</span>{[["today", "오늘"], ["last7", "최근 7일"], ["last30", "최근 30일"]].map(([key, label]) => <button type="button" key={key} className={filters.period === key ? "is-active" : ""} onClick={() => quick("period", key)}>{label}</button>)}<span>접속 위치</span>{[["internal", "내부망"], ["external", "외부망"]].map(([key, label]) => <button type="button" key={key} className={filters.accessType === key ? "is-active" : ""} onClick={() => quick("accessType", key)}>{label}</button>)}</div>
      </div>
    </form>
    {state.error ? <p className="user-management-error">{state.error}</p> : null}
    <div className="audit-log-summary-row"><span>총 {state.total.toLocaleString("ko-KR")}건</span><button type="button" className="audit-export-button" onClick={exportExcel} disabled={downloadBusy || downloading}>{downloading ? "준비 중..." : "엑셀 다운로드"}</button></div>
    <div className="access-log-table-wrap"><table className="access-log-table audit-log-table"><thead><tr><th>작업 상태</th><th>작업 유형</th><th>사용자 ID</th><th>사용자 이름</th><th>메뉴</th><th>대상</th><th>작업 내용</th><th>접속 IP</th><th>접속 구분</th><th>작업 일시</th><th>상세</th></tr></thead><tbody>
      {state.loading ? <tr><td colSpan="11">불러오는 중...</td></tr> : null}
      {!state.loading && state.items.length === 0 ? <tr className="access-log-empty-row"><td colSpan="11">조회된 감사로그가 없습니다.</td></tr> : null}
      {!state.loading && state.items.map((item) => <tr key={item.id}><td><span className={`audit-action-badge is-${item.action_type}`}>{ACTION_LABELS[item.action_type] || item.action_type}</span></td><td>{item.action_type}</td><td>{item.username}</td><td>{item.user_name}</td><td>{item.menu_name}</td><td title={`${item.target_type} #${item.target_id || "-"}`}>{item.target_name || "-"}</td><td className="audit-summary-cell" title={item.action_summary}>{item.action_summary}{item.changed_fields?.length ? <small>{item.changed_fields.map(labelField).join(", ")} · {item.changed_fields.length}개 항목 변경</small> : null}</td><td>{item.ip_address || "-"}</td><td><span className={`access-type-badge is-${item.access_type}`}>{item.access_type === "internal" ? "내부망" : "외부망"}</span></td><td>{formatDate(item.occurred_at)}</td><td><button type="button" className="audit-detail-button" onClick={() => openDetail(item.id)}>상세보기</button></td></tr>)}
    </tbody></table></div>
    <div className="access-log-pagination"><button type="button" disabled={page <= 1 || state.loading} onClick={() => setPage((v) => v - 1)}>이전</button><span>{page} / {state.pages}</span><button type="button" disabled={page >= state.pages || state.loading} onClick={() => setPage((v) => v + 1)}>다음</button></div>
    {detail.open ? <AuditDetailModal state={detail} onClose={() => setDetail({ open: false, loading: false, item: null, error: "" })} /> : null}
  </section>;
}

function buildQuery(filters, page) { const query = { keyword: filters.keyword, username: filters.username }; if (page) Object.assign(query, { page, page_size: 50 }); if (filters.menuKey) query.menu_key = filters.menuKey; if (filters.actionType) query.action_type = filters.actionType; if (filters.targetType) query.target_type = filters.targetType; if (filters.accessType) query.access_type = filters.accessType; if (filters.changedField) query.changed_field = normalizeField(filters.changedField); const range = dateRange(filters); if (range.start) query.start_date = range.start; if (range.end) query.end_date = range.end; return query; }
function dateRange(filters) { if (filters.period === "custom") return { start: filters.startDate, end: filters.endDate }; if (!filters.period) return {}; const end = new Date(); const start = new Date(); if (filters.period === "last7") start.setDate(start.getDate() - 6); if (filters.period === "last30") start.setDate(start.getDate() - 29); return { start: key(start), end: key(end) }; }
function key(date) { const pad = (v) => String(v).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`; }
function formatDate(value) { const date = new Date(value); if (Number.isNaN(date.getTime())) return value || "-"; const pad = (v) => String(v).padStart(2, "0"); return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`; }
function labelField(field) { return FIELD_LABELS[field] || field; }
function normalizeField(value) { const entry = Object.entries(FIELD_LABELS).find(([, label]) => label.toLowerCase() === value.trim().toLowerCase()); return entry ? entry[0] : value.trim(); }
function displayValue(value, field) { if (value === null || value === undefined) return "-"; if (value === "") return "(빈 값)"; if (Array.isArray(value)) return value.map((item) => field === "menu_permissions" ? (PERMISSION_LABELS[item] || item) : item).join(", ") || "(빈 값)"; if (typeof value === "object") return Object.entries(value).map(([key, item]) => `${labelField(key)}: ${displayValue(item, key)}`).join(" / "); return String(value); }

function AuditDetailModal({ state, onClose }) { const item = state.item; const fields = item?.changed_fields || []; const mode = item?.action_type === "create" ? "등록 정보" : item?.action_type === "delete" ? "삭제된 정보" : "변경 상세"; const displayFields = fields.length ? fields : Object.keys(item?.after_data || item?.before_data || {}); return <div className="audit-detail-backdrop" onMouseDown={onClose}><section className="audit-detail-modal" role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}><header><div><h3>감사로그 상세</h3><p>{item?.action_summary || "작업 상세 정보"}</p></div><button type="button" onClick={onClose}>닫기</button></header>{state.loading ? <p>불러오는 중...</p> : null}{state.error ? <p className="user-management-error">{state.error}</p> : null}{item ? <><dl className="audit-detail-meta"><div><dt>작업 일시</dt><dd>{formatDate(item.occurred_at)}</dd></div><div><dt>사용자</dt><dd>{item.username} / {item.user_name}</dd></div><div><dt>메뉴</dt><dd>{item.menu_name}</dd></div><div><dt>작업 유형</dt><dd>{ACTION_LABELS[item.action_type] || item.action_type}</dd></div><div><dt>대상</dt><dd>{item.target_type} / {item.target_name || "-"}</dd></div><div><dt>접속 정보</dt><dd>{item.ip_address || "-"} / {item.access_type === "internal" ? "내부망" : "외부망"}</dd></div><div><dt>환경</dt><dd>{item.browser || "-"} / {item.operating_system || "-"}</dd></div></dl><h4>{mode}</h4>{displayFields.length ? <div className="audit-detail-table-wrap"><table><thead><tr><th>항목</th>{item.action_type !== "create" ? <th>변경 전</th> : null}{item.action_type !== "delete" ? <th>변경 후</th> : null}</tr></thead><tbody>{displayFields.map((field) => <tr key={field}><th>{labelField(field)}</th>{item.action_type !== "create" ? <td>{displayValue(item.before_data?.[field], field)}</td> : null}{item.action_type !== "delete" ? <td>{displayValue(item.after_data?.[field], field)}</td> : null}</tr>)}</tbody></table></div> : <p className="audit-detail-empty">상세 변경 정보가 없습니다.</p>}</> : null}</section></div>; }
