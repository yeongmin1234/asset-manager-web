import React from "react";

function OrderEmptyTable({ columns, emptyMessage }) {
  return (
    <div className="online-order-table-scroll">
      <table className="online-order-skeleton-table">
        <thead><tr>{columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
        <tbody><tr><td colSpan={columns.length} className="online-order-empty-cell">{emptyMessage}</td></tr></tbody>
      </table>
    </div>
  );
}

export default OrderEmptyTable;
