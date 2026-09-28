import React from "react";

const SUMMARY_ITEMS = [
  { key: "total", label: "전체 대상" },
  { key: "received", label: "접수 완료" },
  { key: "orders", label: "주문 대상" },
  { key: "shipped", label: "발송 완료" },
];

function RecallSummaryCards({ summary = {} }) {
  return (
    <section className="online-summary-grid" aria-label="리콜 현황 요약">
      {SUMMARY_ITEMS.map(({ key, label }) => (
        <div className="online-summary-card" key={key}>
          <span>{label}</span>
          <strong>{summary[key] ?? 0}</strong>
        </div>
      ))}
    </section>
  );
}

export default RecallSummaryCards;
