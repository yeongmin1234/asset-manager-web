import React from "react";

const SUMMARY_ITEMS = [
  { key: "inProgress", label: "진행 중 업무" },
  { key: "needsReview", label: "확인 필요" },
  { key: "completedToday", label: "오늘 처리" },
];

function OnlineSummaryCards({ summary = {} }) {
  return (
    <section className="online-summary-grid" aria-label="온라인 업무 요약">
      {SUMMARY_ITEMS.map(({ key, label }) => (
        <div className="online-summary-card" key={key}>
          <span>{label}</span>
          <strong>{summary[key] ?? 0}</strong>
        </div>
      ))}
    </section>
  );
}

export default OnlineSummaryCards;
