import React from "react";

const SUMMARY_ITEMS = [
  { key: "total_count", label: "전체 대상" },
  { key: "received_count", label: "접수완료" },
  { key: "remaining_count", label: "잔여" },
  { key: "in_progress_count", label: "진행중" },
  { key: "shipped_count", label: "발송완료" },
];

function RecallSummaryCards({ summary = {} }) {
  return (
    <section className="online-summary-grid online-recall-summary-grid" aria-label="리콜 현황 요약">
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
