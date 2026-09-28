import React from "react";
import { displayRecallStatus, formatPhoneForDisplay, formatRecallDate, recallStatusClass } from "./onlineDisplayUtils.js";

const COLUMNS = [
  { label: "신청일자", width: 100 },
  { label: "수량", width: 64 },
  { label: "성함", width: 100 },
  { label: "연락처", width: 130 },
  { label: "주소지", width: 240 },
  { label: "메모", width: 240 },
  { label: "시리얼번호", width: 140 },
  { label: "LOT 번호", width: 110 },
  { label: "기존 필터 회수 동의", width: 150 },
  { label: "회수 일자", width: 100 },
  { label: "대체 필터 출고 동의", width: 155 },
  { label: "현재 상태", width: 100 },
  { label: "작업", width: 80 },
];

const show = (value) => value === null || value === undefined || value === "" ? "-" : value;

function RecallTable({ items = [], isLoading = false, error = "", onOpenDetail }) {
  let content;
  if (isLoading) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty">목록을 불러오는 중입니다.</td></tr>;
  } else if (error) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty online-recall-error">{error}</td></tr>;
  } else if (!items.length) {
    content = <tr><td colSpan={COLUMNS.length} className="online-recall-empty">등록된 리콜 데이터가 없습니다.</td></tr>;
  } else {
    content = items.map((item) => (
      <tr key={item.id}>
        <td>{formatRecallDate(item.application_date)}</td>
        <td>{show(item.quantity)}</td>
        <td>{show(item.customer_name)}</td>
        <td title={item.phone_normalized ? `비교용: ${item.phone_normalized}` : undefined}>{show(formatPhoneForDisplay(item.phone_original))}</td>
        <td className="online-recall-long-cell" title={item.address || undefined}><span>{show(item.address)}</span></td>
        <td className="online-recall-long-cell" title={item.memo || undefined}><span>{show(item.memo)}</span></td>
        <td>{show(item.serial_number)}</td>
        <td>{show(item.lot_number)}</td>
        <td>{show(item.pickup_agreement)}</td>
        <td>{formatRecallDate(item.pickup_date)}</td>
        <td>{show(item.replacement_shipping_agreement)}</td>
        <td><span className={`online-recall-status ${recallStatusClass(item.current_status)}`}>{displayRecallStatus(item.current_status)}</span></td>
        <td><button type="button" className="secondary-button online-recall-detail-button" onClick={() => onOpenDetail(item.id)}>상세</button></td>
      </tr>
    ));
  }

  return (
    <div className="online-recall-table-wrap">
      <table className="online-recall-table">
        <colgroup>{COLUMNS.map((column) => <col key={column.label} style={{ width: column.width }} />)}</colgroup>
        <thead><tr>{COLUMNS.map((column) => <th scope="col" key={column.label}>{column.label}</th>)}</tr></thead>
        <tbody>{content}</tbody>
      </table>
    </div>
  );
}

export default RecallTable;
