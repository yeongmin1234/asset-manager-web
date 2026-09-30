import React from "react";

const number = (value) => Number(value || 0).toLocaleString("ko-KR");
const percent = (value, total) => total > 0 ? (Number(value || 0) / total * 100).toFixed(1) : "0.0";
const barWidth = (value, total) => `${Math.min(100, Math.max(0, Number(percent(value, total))))}%`;

const PROGRESS_ITEMS = [
  ["total_count", "전체 대상", "total"],
  ["received_count", "신청 완료", "received"],
  ["remaining_count", "잔여(미신청)", "remaining"],
  ["in_progress_count", "진행중", "progress"],
  ["shipped_count", "발송완료", "shipped"],
];

export function RecallTargetProgressCards({ summary = {} }) {
  const total = Number(summary.total_count || 0);
  return <section className="online-target-progress-cards" aria-label="리콜 대상 진행 현황">
    {PROGRESS_ITEMS.map(([key, label, tone]) => <div className="online-target-progress-card" data-tone={tone} key={key}>
      <span className="online-target-progress-title">{label}</span>
      <strong>{number(summary[key])}</strong>
      <div className="online-target-progress-bottom"><span className="online-target-progress-track"><span style={{ width: barWidth(summary[key], total) }} /></span><small>{percent(summary[key], total)}%</small></div>
    </div>)}
  </section>;
}

const QUALITY_ITEMS = [
  ["normal_count", "정상", "normal", "✓"],
  ["duplicate_count", "중복", "duplicate", "≡"],
  ["review_count", "확인 필요", "review", "!"],
];

export function RecallTargetQualityCards({ summary = {} }) {
  return <section className="online-target-quality-cards" aria-label="Raw 데이터 품질 현황">
    {QUALITY_ITEMS.map(([key, label, tone, icon]) => <div className="online-target-quality-card" data-tone={tone} key={key}>
      <span className="online-target-quality-icon" aria-hidden="true">{icon}</span>
      <div><span>{label}</span><strong>{number(summary[key])}</strong></div>
    </div>)}
  </section>;
}

export function RecallChannelProgress({ channels = [] }) {
  return <section className="online-target-overview-card" aria-label="채널별 진행 현황">
    <h3>채널별 진행 현황</h3>
    <div className="online-target-table-wrap"><table className="online-target-channel-table"><thead><tr><th>판매채널</th><th>전체 대상</th><th>신청 완료</th><th>미접수</th><th>확인 필요</th><th>진행중</th><th>발송완료</th><th>신청률</th></tr></thead><tbody>
      {channels.length ? channels.map((channel) => <tr key={channel.sales_channel}>
        <td>{channel.sales_channel || "미지정"}</td><td>{number(channel.total_count)}</td><td>{number(channel.matched_count)}</td><td>{number(channel.unmatched_count)}</td><td>{number(channel.review_count)}</td><td>{number(channel.in_progress_count)}</td><td>{number(channel.shipped_count)}</td>
        <td><div className="online-target-channel-rate"><span>{Number(channel.application_rate || 0).toFixed(1)}%</span><span className="online-target-progress-track"><span style={{ width: barWidth(channel.matched_count, channel.total_count) }} /></span></div></td>
      </tr>) : <tr><td colSpan={8}>등록된 판매채널이 없습니다.</td></tr>}
    </tbody></table></div>
  </section>;
}

const STAGES = [
  ["total_count", "리콜 대상", "total"],
  ["received_count", "신청 완료", "received"],
  ["in_progress_count", "진행중", "progress"],
  ["order_count", "SCM 발주", "order"],
  ["shipped_count", "발송완료", "shipped"],
];

export function RecallStageProgress({ summary = {} }) {
  const total = Number(summary.total_count || 0);
  return <section className="online-target-overview-card" aria-label="진행 단계별 현황">
    <h3>진행 단계별 현황</h3>
    <div className="online-target-stages">{STAGES.map(([key, label, tone], index) => <React.Fragment key={key}>
      {index > 0 && <span className="online-target-stage-arrow" aria-hidden="true">›</span>}
      <div className="online-target-stage" data-tone={tone}><span>{label}</span><strong>{number(summary[key])}</strong><small>{percent(summary[key], total)}%</small></div>
    </React.Fragment>)}</div>
    <p>전체 대상 {number(total)}건 중 {number(summary.received_count)}건이 신청했습니다. 신청률 {percent(summary.received_count, total)}%</p>
  </section>;
}
