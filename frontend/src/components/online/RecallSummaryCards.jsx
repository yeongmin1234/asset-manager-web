import React from "react";

const SUMMARY_ITEMS = [
  { key: "total_count", label: "전체 대상", tone: "total" },
  { key: "received_count", label: "신청 완료", tone: "received" },
  { key: "remaining_count", label: "잔여", tone: "remaining" },
  { key: "in_progress_count", label: "진행중", tone: "progress" },
  { key: "shipped_count", label: "발송완료", tone: "shipped" },
];

function RecallSummaryCards({ summary = {} }) {
  return (
    <section className="online-summary-grid online-recall-summary-grid" aria-label="리콜 현황 요약">
      {SUMMARY_ITEMS.map(({ key, label, tone }) => (
        <div className="online-summary-card" data-tone={tone} key={key}>
          <span>{label}</span>
          <strong>{summary[key] ?? 0}</strong>
        </div>
      ))}
    </section>
  );
}

export default RecallSummaryCards;
