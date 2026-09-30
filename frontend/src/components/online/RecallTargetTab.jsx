import React, { useEffect, useState } from "react";
import { getRecallMatchingSummary, getRecallTargetBatches, getRecallTargetChannels, getRecallTargets, getRecallTargetSummary, runRecallTargetMatching } from "../../api/client.js";
import { formatPhoneForDisplay } from "./onlineDisplayUtils.js";
import RecallPageSizeSelect from "./RecallPageSizeSelect.jsx";
import RecallTargetDetailModal from "./RecallTargetDetailModal.jsx";

const HEADERS = [["sales_channel", "판매채널"], ["original_order_no", "주문번호"], ["customer_name", "고객명"], ["phone_raw", "연락처"], ["address", "주소"], ["delivery_message", "배송메시지"], ["serial_number", "시리얼번호"], ["lot_number", "LOT 번호"], ["purchase_date", "구매일"]];

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
  useEffect(() => {
    let active = true;
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
  return <div className="online-target-panel">
    <section className="online-order-summary online-target-summary online-target-raw-summary" aria-label="리콜 대상 요약">{[["total_count", "전체 대상", "total"], ["normal_count", "정상", "normal"], ["duplicate_count", "중복", "duplicate"], ["review_count", "확인 필요", "review"]].map(([key, label, tone]) => <div key={key} data-tone={tone}><span>{label}</span><strong>{summary[key] ?? 0}</strong></div>)}</section>
    <section className="online-order-summary online-target-summary" aria-label="리콜 신청 매칭 요약">{[["received_count", "신청 완료"], ["remaining_count", "잔여"], ["in_progress_count", "진행중"], ["shipped_count", "발송완료"]].map(([key, label]) => <div key={key}><span>{label}</span><strong>{matchSummary[key] ?? 0}</strong></div>)}</section>
    <nav className="online-target-subtabs" aria-label="리콜 대상 화면"><button type="button" className={view === "list" ? "active" : ""} aria-current={view === "list" ? "page" : undefined} onClick={() => setView("list")}>리콜 대상 목록</button><button type="button" className={view === "batches" ? "active" : ""} aria-current={view === "batches" ? "page" : undefined} onClick={() => setView("batches")}>업로드 Batch 이력</button></nav>
    {view === "list" && <>
    <section className="online-recall-list" aria-label="리콜 대상 목록">
      <form className="online-target-filters" onSubmit={(event) => { event.preventDefault(); setPage(1); setAppliedKeyword(keyword.trim()); }}>
        <input aria-label="리콜 대상 검색" placeholder="고객명, 연락처, 주문번호, 시리얼번호" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
        <select aria-label="리콜 대상 상태" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">전체</option><option value="valid">정상</option><option value="duplicate">중복</option><option value="review">확인 필요</option></select>
        <select aria-label="신청 상태" value={matchStatus} onChange={(event) => { setMatchStatus(event.target.value); setPage(1); }}><option value="">신청 상태 전체</option><option value="MATCHED">신청완료</option><option value="UNMATCHED">미접수</option><option value="REVIEW">매칭 확인 필요</option></select>
        <button type="submit" className="primary-action">검색</button>
        <button type="button" className="secondary-button" onClick={() => { setKeyword(""); setAppliedKeyword(""); setStatus(""); setMatchStatus(""); setPage(1); }}>초기화</button>
      </form>
      <div className="online-target-toolbar"><span>총 {listing.total}건</span><RecallPageSizeSelect value={pageSize} onChange={(value) => { setPage(1); onPageSizeChange(value); }} disabled={loading} /><button type="button" className="secondary-button" onClick={rerun} disabled={matching}>기존 데이터 매칭 실행</button></div>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      <div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>상태</th>{HEADERS.map(([key, label]) => <th key={key}>{label}</th>)}<th>신청 여부</th><th>매칭 기준</th><th>현재 진행 상태</th><th>사유</th><th>작업</th></tr></thead><tbody>{loading ? <tr><td colSpan={15}>불러오는 중...</td></tr> : listing.items?.length ? listing.items.map((item) => <tr key={item.id}>
        <td><span className={`online-preview-badge online-preview-badge-${item.duplicate_flag ? "duplicate" : item.review_required ? "review" : "valid"}`}>{item.duplicate_flag ? "중복" : item.review_required ? "확인 필요" : "정상"}</span></td>{HEADERS.map(([key]) => <td key={key}><span className="online-target-cell-text" title={String(item[key] ?? "")}>{key === "phone_raw" ? formatPhoneForDisplay(item[key] || "") : item[key] || "-"}</span></td>)}<td className={`online-match-status-${item.match_status}`}>{item.match_status === "MATCHED" ? "신청완료" : item.match_status === "REVIEW" ? "확인 필요" : "미접수"}</td><td>{item.match_method || "-"}</td><td>{item.application_status || "-"}</td><td><span className="online-target-cell-text" title={[item.duplicate_reason, item.review_reason, item.match_review_reason].filter(Boolean).join(", ")}>{[item.duplicate_reason, item.review_reason, item.match_review_reason].filter(Boolean).join(", ") || "-"}</span></td><td><button type="button" className="secondary-button" onClick={() => setDetailId(item.id)}>상세</button></td>
      </tr>) : <tr><td colSpan={15}>해당 리콜 대상이 없습니다.</td></tr>}</tbody></table></div>
      <div className="online-recall-pagination"><span>{page}/{listing.total_pages || 1} 페이지</span><div><button type="button" className="secondary-button" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>이전</button><button type="button" className="secondary-button" disabled={page >= (listing.total_pages || 1) || loading} onClick={() => setPage(page + 1)}>다음</button></div></div>
    </section>
    <section className="online-recall-list" aria-label="채널별 리콜 진행 현황"><h3>채널별 진행 현황</h3><div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>판매채널</th><th>전체 대상</th><th>신청 완료</th><th>미접수</th><th>확인 필요</th><th>진행중</th><th>발송완료</th><th>신청률</th></tr></thead><tbody>{channels.map((channel) => <tr key={channel.sales_channel}><td>{channel.sales_channel}</td><td>{channel.total_count}</td><td>{channel.matched_count}</td><td>{channel.unmatched_count}</td><td>{channel.review_count}</td><td>{channel.in_progress_count}</td><td>{channel.shipped_count}</td><td>{channel.application_rate}%</td></tr>)}</tbody></table></div></section>
    </>}
    {view === "batches" && <section className="online-recall-list" aria-label="리콜 대상 업로드 이력"><h3>업로드 Batch 이력</h3><div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>등록일</th><th>파일</th><th>전체</th><th>정상</th><th>중복</th><th>확인 필요</th><th>제외</th></tr></thead><tbody>{batches.map((batch) => <tr key={batch.id}><td>{batch.created_at?.slice(0, 10)}</td><td>{batch.original_filename}</td><td>{batch.total_count}</td><td>{batch.normal_count}</td><td>{batch.duplicate_count}</td><td>{batch.review_count}</td><td>{batch.excluded_count}</td></tr>)}</tbody></table></div></section>}
    {detailId !== null && <RecallTargetDetailModal targetId={detailId} onClose={() => setDetailId(null)} onChanged={() => setLocalRefresh((value) => value + 1)} onApplicationDetail={onApplicationDetail} />}
  </div>;
}

export default RecallTargetTab;
