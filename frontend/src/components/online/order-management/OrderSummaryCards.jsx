import React from "react";

function OrderSummaryCards({ items }) {
  return (
    <div className="online-order-stat-grid">
      {items.map(({ label, value }) => (
        <div className="online-summary-card" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

export default OrderSummaryCards;
