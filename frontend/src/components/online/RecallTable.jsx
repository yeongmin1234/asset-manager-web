import React, { useEffect, useRef } from "react";
import { displayRecallReviewReasons, displayRecallStatus, formatPhoneForDisplay, formatRecallDate, isRecallBulkSelectable, recallStatusClass } from "./onlineDisplayUtils.js";

const COLUMNS = [
  { label: "선택", width: 48 },
  { label: "신청일자", width: 100 },
  { label: "수량", width: 64 },
  { label: "성함", width: 100 },
  { label: "연락처", width: 130 },
  { label: "주소지", width: 240 },
  { label: "메모", width: 240 },
  { label: "현재 상태", width: 100 },
  { label: "확인 필요 사유", width: 235 },
  { label: "시리얼번호", width: 140 },
  { label: "LOT 번호", width: 110 },
  { label: "기존 필터 회수 동의", width: 150 },
  { label: "회수 일자", width: 100 },
  { label: "대체 필터 출고 동의", width: 155 },
  { label: "작업", width: 80 },
];

const show = (value) => value === null || value === undefined || value === "" ? "-" : value;

function RecallTable({ items = [], isLoading = false, isBulkUpdating = false, selectAllRows = false, error = "", selectedIds, onToggleSelection, onTogglePage, onOpenDetail }) {
  const selectAllRef = useRef(null);
  const eligibleItems = items.filter((item) => selectAllRows || isRecallBulkSelectable(item.workflow_status || item.current_status));
  const selectedOnPage = eligibleItems.filter((item) => selectedIds.has(item.id)).length;
  const allSelected = eligibleItems.length > 0 && selectedOnPage === eligibleItems.length;

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = selectedOnPage > 0 && !allSelected;
  }, [selectedOnPage, allSelected]);

  let content;
  if (isLoading) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty">목록을 불러오는 중입니다.</td></tr>;
  } else if (error) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty online-recall-error">{error}</td></tr>;
  } else if (!items.length) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty">등록된 리콜 데이터가 없습니다.</td></tr>;
  } else {
    content = items.map((item) => (
      <tr key={item.id} className={item.duplicate_flag ? "online-recall-duplicate-row" : undefined}>
        <td>
          <input type="checkbox" checked={selectedIds.has(item.id)} disabled={isLoading || isBulkUpdating || (!selectAllRows && !isRecallBulkSelectable(item.workflow_status || item.current_status))} onChange={() => onToggleSelection(item.id)} aria-label={`${item.customer_name} ${selectAllRows ? "선택" : "상태 변경 선택"}`} title={!selectAllRows && !isRecallBulkSelectable(item.workflow_status || item.current_status) ? "접수 완료 또는 진행중 상태만 선택할 수 있습니다." : undefined} />
        </td>
        <td>{formatRecallDate(item.application_date)}</td>
        <td>{show(item.quantity)}</td>
        <td>{show(item.customer_name)}</td>
        <td title={item.phone_normalized ? `비교용: ${item.phone_normalized}` : undefined}>{show(formatPhoneForDisplay(item.phone_original))}</td>
        <td className="online-recall-long-cell" title={item.address || undefined}><span>{show(item.address)}</span></td>
        <td className="online-recall-long-cell" title={item.memo || undefined}><span>{show(item.memo)}</span></td>
        <td><span className={`online-recall-status ${recallStatusClass(item.workflow_status || item.current_status)}`}>{displayRecallStatus(item.workflow_status || item.current_status)}</span>{(item.current_status === "REVIEW_REQUIRED" || item.review_reason_codes?.length > 0) && <span className="online-recall-review-badge">확인 필요</span>}{item.duplicate_flag && <span className="online-recall-duplicate-badge">중복 확인</span>}</td>
        <td><span className="online-recall-review-reasons" title={displayRecallReviewReasons(item.review_reason_codes)}>{displayRecallReviewReasons(item.review_reason_codes)}</span></td>
        <td>{show(item.serial_number)}</td>
        <td>{show(item.lot_number)}</td>
        <td>{show(item.pickup_agreement)}</td>
        <td>{formatRecallDate(item.pickup_date)}</td>
        <td>{show(item.replacement_shipping_agreement)}</td>
        <td><button type="button" className="secondary-button online-recall-detail-button" onClick={() => onOpenDetail(item.id)}>상세</button></td>
      </tr>
    ));
  }

  return (
    <div className="online-recall-table-wrap">
      <table className="online-recall-table">
        <colgroup>{COLUMNS.map((column) => <col key={column.label} style={{ width: column.width }} />)}</colgroup>
        <thead><tr>{COLUMNS.map((column) => <th scope="col" key={column.label}>
          {column.label === "선택" ? <input ref={selectAllRef} type="checkbox" checked={allSelected} disabled={isLoading || isBulkUpdating || eligibleItems.length === 0} onChange={(event) => onTogglePage(event.target.checked)} aria-label={selectAllRows ? "현재 페이지 전체 선택" : "현재 페이지 상태 변경 가능 건 전체 선택"} /> : column.label}
        </th>)}</tr></thead>
        <tbody>{content}</tbody>
      </table>
    </div>
  );
}

export default RecallTable;
