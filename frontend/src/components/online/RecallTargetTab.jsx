import React, { useEffect, useState } from "react";
import { getRecallTargetBatches, getRecallTargets, getRecallTargetSummary } from "../../api/client.js";
import { formatPhoneForDisplay } from "./onlineDisplayUtils.js";
import RecallPageSizeSelect from "./RecallPageSizeSelect.jsx";

const HEADERS = [["sales_channel", "판매채널"], ["original_order_no", "주문번호"], ["customer_name", "고객명"], ["phone_raw", "연락처"], ["address", "주소"], ["delivery_message", "배송메시지"], ["serial_number", "시리얼번호"], ["lot_number", "LOT 번호"], ["purchase_date", "구매일"]];

function RecallTargetTab({ pageSize, onPageSizeChange, refreshKey }) {
  const [keyword, setKeyword] = useState("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [listing, setListing] = useState({ items: [], total: 0, total_pages: 1 });
  const [summary, setSummary] = useState({});
  const [batches, setBatches] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    Promise.all([getRecallTargets({ keyword: appliedKeyword, status, page, page_size: pageSize }), getRecallTargetSummary(), getRecallTargetBatches()])
      .then(([items, counts, history]) => { if (active) { setListing(items); setSummary(counts); setBatches(history); } })
      .catch((caught) => { if (active) setError(caught?.message || "리콜 대상을 불러오지 못했습니다."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [appliedKeyword, status, page, pageSize, refreshKey]);
  return <div className="online-target-panel">
    <section className="online-order-summary" aria-label="리콜 대상 요약">{[["total_count", "전체 대상"], ["normal_count", "정상"], ["duplicate_count", "중복"], ["review_count", "확인 필요"]].map(([key, label]) => <div key={key}><span>{label}</span><strong>{summary[key] ?? 0}</strong></div>)}</section>
    <section className="online-recall-list" aria-label="리콜 대상 목록">
      <form className="online-target-filters" onSubmit={(event) => { event.preventDefault(); setPage(1); setAppliedKeyword(keyword.trim()); }}>
        <input aria-label="리콜 대상 검색" placeholder="고객명, 연락처, 주문번호, 시리얼번호" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
        <select aria-label="리콜 대상 상태" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">전체</option><option value="valid">정상</option><option value="duplicate">중복</option><option value="review">확인 필요</option></select>
        <button type="submit" className="primary-action">검색</button>
        <button type="button" className="secondary-button" onClick={() => { setKeyword(""); setAppliedKeyword(""); setStatus(""); setPage(1); }}>초기화</button>
      </form>
      <div className="online-target-toolbar"><span>총 {listing.total}건</span><RecallPageSizeSelect value={pageSize} onChange={(value) => { setPage(1); onPageSizeChange(value); }} disabled={loading} /></div>
      {error && <p role="alert">{error}</p>}
      <div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>상태</th>{HEADERS.map(([key, label]) => <th key={key}>{label}</th>)}<th>사유</th><th>Batch</th></tr></thead><tbody>{loading ? <tr><td colSpan={12}>불러오는 중...</td></tr> : listing.items?.length ? listing.items.map((item) => <tr key={item.id}>
        <td>{item.duplicate_flag ? "중복" : item.review_required ? "확인 필요" : "정상"}</td>{HEADERS.map(([key]) => <td key={key} title={String(item[key] ?? "")}>{key === "phone_raw" ? formatPhoneForDisplay(item[key] || "") : item[key] || "-"}</td>)}<td>{[item.duplicate_reason, item.review_reason].filter(Boolean).join(", ") || "-"}</td><td>{item.batch_id}</td>
      </tr>) : <tr><td colSpan={12}>해당 리콜 대상이 없습니다.</td></tr>}</tbody></table></div>
      <div className="online-recall-pagination"><span>{page}/{listing.total_pages || 1} 페이지</span><div><button type="button" className="secondary-button" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>이전</button><button type="button" className="secondary-button" disabled={page >= (listing.total_pages || 1) || loading} onClick={() => setPage(page + 1)}>다음</button></div></div>
    </section>
    <section className="online-recall-list" aria-label="리콜 대상 업로드 이력"><h3>업로드 Batch 이력</h3><div className="online-target-table-wrap"><table className="online-target-table"><thead><tr><th>등록일</th><th>파일</th><th>전체</th><th>정상</th><th>중복</th><th>확인 필요</th><th>제외</th></tr></thead><tbody>{batches.map((batch) => <tr key={batch.id}><td>{batch.created_at?.slice(0, 10)}</td><td>{batch.original_filename}</td><td>{batch.total_count}</td><td>{batch.normal_count}</td><td>{batch.duplicate_count}</td><td>{batch.review_count}</td><td>{batch.excluded_count}</td></tr>)}</tbody></table></div></section>
  </div>;
}

export default RecallTargetTab;
