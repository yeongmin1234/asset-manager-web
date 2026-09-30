import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getRecallApplications, getRecallTargetDetail, manualMatchRecallTarget, unmatchRecallTarget } from "../../api/client.js";
import { formatPhoneForDisplay } from "./onlineDisplayUtils.js";
import RecallReasonText from "./RecallReasonText.jsx";

const FIELDS = [["sales_channel", "판매채널"], ["original_order_no", "주문번호"], ["customer_name", "고객명"], ["phone_raw", "연락처"], ["address", "주소"], ["delivery_message", "배송메시지"], ["serial_number", "시리얼번호"], ["lot_number", "LOT 번호"], ["purchase_date", "구매일"]];
const LABELS = { MATCHED: "신청완료", UNMATCHED: "미접수", REVIEW: "확인 필요" };

function RecallTargetDetailModal({ targetId, onClose, onChanged, onApplicationDetail }) {
  const [detail, setDetail] = useState(null);
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    getRecallTargetDetail(targetId).then((value) => { if (active) setDetail(value); }).catch((caught) => { if (active) setError(caught?.message || "상세 정보를 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [targetId]);
  useEffect(() => {
    const close = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [busy, onClose]);
  const search = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    setBusy(true); setError("");
    try {
      const result = await getRecallApplications({ keyword: query.trim(), page: 1, page_size: 20, include_duplicates: true });
      setCandidates(result.items || []);
    } catch (caught) { setError(caught?.message || "신청 건을 검색하지 못했습니다."); }
    finally { setBusy(false); }
  };
  const confirmMatch = async () => {
    if (!selectedId || !window.confirm(`신청 건 #${selectedId}으로 수동 매칭을 확정하시겠습니까?`)) return;
    setBusy(true); setError("");
    try { await manualMatchRecallTarget(targetId, Number(selectedId)); onChanged(); onClose(); }
    catch (caught) { setError(caught?.message || "매칭을 확정하지 못했습니다."); }
    finally { setBusy(false); }
  };
  const release = async () => {
    if (!window.confirm("이 리콜 대상의 신청 매칭을 해제하시겠습니까?")) return;
    setBusy(true); setError("");
    try { await unmatchRecallTarget(targetId); onChanged(); onClose(); }
    catch (caught) { setError(caught?.message || "매칭을 해제하지 못했습니다."); }
    finally { setBusy(false); }
  };
  const target = detail?.target;
  return createPortal(<div className="online-upload-backdrop" onMouseDown={() => { if (!busy) onClose(); }}>
    <section className="online-upload-modal online-target-detail" role="dialog" aria-modal="true" aria-labelledby="target-detail-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="online-upload-header"><h2 id="target-detail-title">리콜 대상 상세 #{targetId}</h2><button type="button" className="secondary-button" onClick={onClose} disabled={busy}>닫기</button></header>
      {error && <p className="online-upload-error" role="alert">{error}</p>}
      {!target ? <p>불러오는 중...</p> : <div className="online-target-detail-body">
        <h3>리콜 대상 정보</h3><dl>{FIELDS.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{key === "phone_raw" ? formatPhoneForDisplay(target[key] || "") : target[key] || "-"}</dd></div>)}</dl>
        <dl><div><dt>대상 사유</dt><dd><RecallReasonText reasons={[target.duplicate_reason, target.review_reason]} /></dd></div></dl>
        <h3>신청 매칭 정보</h3><dl>
          <div><dt>신청 여부</dt><dd>{LABELS[target.match_status] || target.match_status}</dd></div>
          <div><dt>매칭 기준</dt><dd>{target.match_method || "-"}</dd></div>
          <div><dt>매칭일시</dt><dd>{target.matched_at || "-"}</dd></div>
          <div><dt>연결된 신청 ID</dt><dd>{target.matched_application_id || "-"}</dd></div>
          <div><dt>실제 신청일</dt><dd>{detail.application?.application_date || "-"}</dd></div>
          <div><dt>현재 리콜 상태</dt><dd>{detail.application?.current_status || "-"}</dd></div>
          <div><dt>확인 사유</dt><dd><RecallReasonText reasons={target.match_review_reason} /></dd></div>
        </dl>
        {target.match_status === "MATCHED" ? <div className="online-target-detail-actions"><button type="button" className="secondary-button" onClick={() => { onApplicationDetail?.(target.matched_application_id); onClose(); }}>신청 상세 보기</button><button type="button" className="secondary-button" onClick={release} disabled={busy}>매칭 해제</button></div> : <>
          <h3>신청 건 수동 매칭</h3><form className="online-target-filters" onSubmit={search}><input aria-label="신청 건 검색" placeholder="고객명, 연락처, 시리얼번호 검색" value={query} onChange={(event) => setQuery(event.target.value)} /><button type="submit" className="secondary-button" disabled={busy}>검색</button></form>
          <div className="online-target-candidates">{candidates.map((item) => <label key={item.id}><input type="radio" name="application-candidate" value={item.id} checked={String(selectedId) === String(item.id)} onChange={() => setSelectedId(item.id)} /> #{item.id} {item.customer_name} · {formatPhoneForDisplay(item.phone_original || "")} · {item.serial_number || "시리얼 없음"} {item.duplicate_flag ? "(중복 확인)" : ""}</label>)}</div>
          <button type="button" className="primary-action" onClick={confirmMatch} disabled={!selectedId || busy}>매칭 확정</button>
        </>}
      </div>}
      <footer className="online-upload-footer"><button type="button" className="secondary-button" onClick={onClose} disabled={busy}>닫기</button></footer>
    </section>
  </div>, document.body);
}

export default RecallTargetDetailModal;
