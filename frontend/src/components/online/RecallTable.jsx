import React from "react";
import { displayRecallStatus, formatPhoneForDisplay } from "./onlineDisplayUtils.js";

const COLUMNS = ["판매 채널", "주문번호", "고객명", "연락처", "시리얼번호", "현재 상태", "접수일", "발송일", "작업"];

function formatDate(value) {
  if (!value) return "-";
  return String(value).slice(0, 10);
}

function RecallTable({ items = [], isLoading = false, error = "" }) {
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
        <td>-</td>
        <td>-</td>
        <td>{item.customer_name || "-"}</td>
        <td title={item.phone_normalized ? `비교용: ${item.phone_normalized}` : undefined}>{formatPhoneForDisplay(item.phone_original) || "-"}</td>
        <td>{item.serial_number || "-"}</td>
        <td><span className="online-recall-status">{displayRecallStatus(item.current_status)}</span></td>
        <td>{formatDate(item.created_at)}</td>
        <td>-</td>
        <td>-</td>
      </tr>
    ));
  }

  return (
    <div className="online-recall-table-wrap">
      <table className="online-recall-table">
        <thead><tr>{COLUMNS.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
        <tbody>{content}</tbody>
      </table>
    </div>
  );
}

export default RecallTable;
