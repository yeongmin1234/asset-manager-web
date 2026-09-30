import React, { useEffect, useState } from "react";
import { deleteRecallTargets, getRecallMatchingSummary, getRecallTargetBatches, getRecallTargetChannels, getRecallTargets, getRecallTargetSummary, runRecallTargetMatching } from "../../api/client.js";
import { displayRecallMatchMethod, displayRecallMatchStatus, displayRecallTargetProgress, formatPhoneForDisplay, recallMatchStatusClass } from "./onlineDisplayUtils.js";
import RecallPageSizeSelect from "./RecallPageSizeSelect.jsx";
import RecallTargetDetailModal from "./RecallTargetDetailModal.jsx";
import RecallReasonText from "./RecallReasonText.jsx";
import RecallTargetDeleteModal from "./RecallTargetDeleteModal.jsx";
import { RecallChannelProgress, RecallStageProgress, RecallTargetProgressCards, RecallTargetQualityCards } from "./RecallTargetOverview.jsx";

const HEADERS = [["sales_channel", "판매채널"], ["original_order_no", "주문번호"], ["customer_name", "고객명"], ["phone_raw", "연락처"], ["address", "주소"], ["delivery_message", "배송메시지"], ["serial_number", "시리얼번호"], ["lot_number", "LOT 번호"], ["purchase_date", "구매일"]];

function visiblePages(current, total) {
  const start = Math.max(1, Math.min(current - 2, total - 4));
  const end = Math.min(total, start + 4);
  const pages = [];
  if (start > 1) pages.push(1, ...(start > 2 ? ["before"] : []));
  for (let number = start; number <= end; number += 1) pages.push(number);
  if (end < total) pages.push(...(end < total - 1 ? ["after"] : []), total);
  return pages;
}

export function RecallTargetMatchCells({ item }) {
  return <>
    <td><span className={`online-target-match-badge online-target-match-${recallMatchStatusClass(item.match_status)}`}>{displayRecallMatchStatus(item.match_status)}</span></td>
    <td>{displayRecallMatchMethod(item.match_method)}</td>
    <td>{displayRecallTargetProgress(item.application_status, item.match_status)}</td>
  </>;
}

function RecallTargetTab({ pageSize, onPageSizeChange, refreshKey, onApplicationDetail }) {
  const [keyword, setKeyword] = useState("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [status, setStatus] = useState("");
  const [matchStatus, setMatchStatus] = useState("");
  const [view, setView] = useState("list");
  const [page, setPage] = useState(1);
  const [listing, setListing] = useState({ items: [], total: 0, total_pages: 1 });
  const [summary, setSummary] = useState({});
  const [matchSummary, setMatchSummary] = useState({});
  const [batches, setBatches] = useState([]);
  const [channels, setChannels] = useState([]);
  const [detailId, setDetailId] = useState(null);
  const [localRefresh, setLocalRefresh] = useState(0);
  const [matching, setMatching] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  useEffect(() => {
    let active = true;
    setSelectedIds(new Set());
    setLoading(true); setError("");
    Promise.all([getRecallTargets({ keyword: appliedKeyword, status, match_status: matchStatus, page, page_size: pageSize }), getRecallTargetSummary(), getRecallTargetBatches(), getRecallTargetChannels(), getRecallMatchingSummary()])
      .then(([items, counts, history, channelStats, matchingCounts]) => { if (active) { setListing(items); setSummary(counts); setBatches(history); setChannels(channelStats); setMatchSummary(matchingCounts); } })
      .catch((caught) => { if (active) setError(caught?.message || "리콜 대상을 불러오지 못했습니다."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [appliedKeyword, status, matchStatus, page, pageSize, refreshKey, localRefresh]);
  const rerun = async () => {
    if (matching || !window.confirm("미접수·확인 필요 대상의 신청 매칭을 다시 실행하시겠습니까?")) return;
    setMatching(true); setError(""); setMessage("");
    try {
      const result = await runRecallTargetMatching();
      setMessage(`매칭 완료: 신청완료 ${result.matched}건 · 확인 필요 ${result.review}건 · 미접수 ${result.unmatched}건`);
      setLocalRefresh((value) => value + 1);
    } catch (caught) { setError(caught?.message || "매칭을 다시 실행하지 못했습니다."); }
    finally { setMatching(false); }
  };
  const pageIds = (listing.items || []).map((item) => item.id);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));
  const selectedMatched = (listing.items || []).some((item) => selectedIds.has(item.id) && (item.match_status === "MATCHED" || item.matched_application_id != null));
  const toggleSelected = (id) => setSelectedIds((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const deleteSelected = async (reason) => {
    if (!selectedIds.size || selectedMatched || deleting) return;
    setDeleting(true); setDeleteError("");
    try {
      const result = await deleteRecallTargets([...selectedIds], reason);
      setDeleteOpen(false); setSelectedIds(new Set());
      setMessage(`${result.deleted}건의 리콜 대상을 삭제했습니다.`);
      setPage(1); setLocalRefresh((value) => value + 1);
    } catch (caught) { setDeleteError(caught?.message || "리콜 대상을 삭제하지 못했습니다."); }
    finally { setDeleting(false); }
  };
  return <div className="online-target-panel">
    <RecallTargetProgressCards summary={matchSummary} />
    <RecallTargetQualityCards summary={summary} />
    <div className="online-target-overview-grid"><RecallChannelProgress channels={channels} /><RecallStageProgress summary={matchSummary} /></div>
    <nav className="online-target-subtabs" aria-label="리콜 대상 화면"><button type="button" className={view === "list" ? "active" : ""} aria-current={view === "list" ? "page" : undefined} onClick={() => setView("list")}>리콜 대상 목록</button><button type="button" className={view === "batches" ? "active" : ""} aria-current={view === "batches" ? "page" : undefined} onClick={() => setView("batches")}>업로드 Batch 이력</button></nav>
    {view === "list" && <>
    <section className="online-recall-list" aria-label="리콜 대상 목록">
      <form className="online-target-filters" onSubmit={(event) => { event.preventDefault(); setPage(1); setAppliedKeyword(keyword.trim()); }}>
        <input aria-label="리콜 대상 검색" placeholder="고객명, 연락처, 주문번호, 시리얼번호" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
        <select aria-label="리콜 대상 상태" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">전체</option><option value="valid">정상</option><option value="duplicate">중복</option><option value="review">확인 필요</option></select>
        <select aria-label="신청 상태" value={matchStatus} onChange={(event) => { setMatchStatus(event.target.value); setPage(1); }}><option value="">신청 상태 전체</option><option value="MATCHED">{displayRecallMatchStatus("MATCHED")}</option><option value="UNMATCHED">{displayRecallMatchStatus("UNMATCHED")}</option><option value="REVIEW">{displayRecallMatchStatus("REVIEW")}</option></select>
        <button type="submit" className="primary-action">조회</button>
        <button type="button" className="secondary-button" onClick={() => { setKeyword(""); setAppliedKeyword(""); setStatus(""); setMatchStatus(""); setPage(1); }}>초기화</button>
      </form>
      <div className="online-target-toolbar"><span>총 {listing.total}건{selectedIds.size > 0 ? ` · ${selectedIds.size}건 선택` : ""}</span><RecallPageSizeSelect value={pageSize} onChange={(value) => { setPage(1); onPageSizeChange(value); }} disabled={loading} /><button type="button" className="secondary-button online-recall-delete-button" disabled={!selectedIds.size || loading || deleting} onClick={() => { setDeleteError(""); setDeleteOpen(true); }}>삭제</button><button type="button" className="secondary-button" onClick={rerun} disabled={matching || deleting}>기존 데이터 매칭 실행</button></div>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      <div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th><input type="checkbox" aria-label="현재 페이지 전체 선택" checked={allPageSelected} disabled={loading || !pageIds.length} onChange={() => setSelectedIds(allPageSelected ? new Set() : new Set(pageIds))} /></th><th>No</th><th>상태</th>{HEADERS.map(([key, label]) => <th key={key}>{label}</th>)}<th>신청 여부</th><th>매칭 기준</th><th>현재 진행 상태</th><th>사유</th><th>등록일</th><th>작업</th></tr></thead><tbody>{loading ? <tr><td colSpan={18}>불러오는 중...</td></tr> : listing.items?.length ? listing.items.map((item, index) => <tr key={item.id}>
        <td><input type="checkbox" aria-label={`리콜 대상 ${item.id} 선택`} checked={selectedIds.has(item.id)} disabled={deleting} onChange={() => toggleSelected(item.id)} /></td><td>{(page - 1) * pageSize + index + 1}</td><td><span className={`online-preview-badge online-preview-badge-${item.duplicate_flag ? "duplicate" : item.review_required ? "review" : "valid"}`}>{item.duplicate_flag ? "중복" : item.review_required ? "확인 필요" : "정상"}</span></td>{HEADERS.map(([key]) => <td key={key}><span className="online-target-cell-text" title={String(item[key] ?? "")}>{key === "phone_raw" ? formatPhoneForDisplay(item[key] || "") : item[key] || "-"}</span></td>)}<RecallTargetMatchCells item={item} /><td><RecallReasonText reasons={[item.duplicate_reason, item.review_reason, item.match_review_reason]} /></td><td>{item.created_at?.slice(0, 10) || "-"}</td><td><button type="button" className="secondary-button" onClick={() => setDetailId(item.id)}>상세</button></td>
      </tr>) : <tr><td colSpan={18}>해당 리콜 대상이 없습니다.</td></tr>}</tbody></table></div>
      <div className="online-target-pagination"><span>총 {listing.total}건 중 {listing.total ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, listing.total)}건</span><div><button type="button" className="secondary-button" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>이전</button>{visiblePages(page, listing.total_pages || 1).map((number) => typeof number === "number" ? <button type="button" key={number} className={`online-target-page-number${number === page ? " active" : ""}`} aria-current={number === page ? "page" : undefined} disabled={loading} onClick={() => setPage(number)}>{number}</button> : <span key={number} aria-hidden="true">…</span>)}<button type="button" className="secondary-button" disabled={page >= (listing.total_pages || 1) || loading} onClick={() => setPage(page + 1)}>다음</button></div></div>
    </section>
    </>}
    {view === "batches" && <section className="online-recall-list" aria-label="리콜 대상 업로드 이력"><h3>업로드 Batch 이력</h3><div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>등록일</th><th>파일</th><th>전체</th><th>정상</th><th>중복</th><th>확인 필요</th><th>제외</th></tr></thead><tbody>{batches.map((batch) => <tr key={batch.id}><td>{batch.created_at?.slice(0, 10)}</td><td>{batch.original_filename}</td><td>{batch.total_count}</td><td>{batch.normal_count}</td><td>{batch.duplicate_count}</td><td>{batch.review_count}</td><td>{batch.excluded_count}</td></tr>)}</tbody></table></div></section>}
    {detailId !== null && <RecallTargetDetailModal targetId={detailId} onClose={() => setDetailId(null)} onChanged={() => setLocalRefresh((value) => value + 1)} onApplicationDetail={onApplicationDetail} />}
    {deleteOpen && <RecallTargetDeleteModal count={selectedIds.size} blocked={selectedMatched} saving={deleting} error={deleteError} onClose={() => setDeleteOpen(false)} onConfirm={deleteSelected} />}
  </div>;
}

export default RecallTargetTab;
