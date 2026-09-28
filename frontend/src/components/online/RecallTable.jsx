import React from "react";

const COLUMNS = ["판매 채널", "주문번호", "고객명", "연락처", "시리얼번호", "현재 상태", "접수일", "발송일", "작업"];

function RecallTable() {
  return (
    <div className="online-recall-table-wrap">
      <table className="online-recall-table">
        <thead>
          <tr>{COLUMNS.map((column) => <th scope="col" key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          <tr><td colSpan={COLUMNS.length} className="online-recall-empty">등록된 리콜 데이터가 없습니다.</td></tr>
        </tbody>
      </table>
    </div>
  );
}

export default RecallTable;
