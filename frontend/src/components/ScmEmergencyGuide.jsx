import React from "react";

const DECISION_RULES = [
  { label: "정상", text: "Ping/SSH 가능 + 3306 응답 가능" },
  { label: "Freeze 의심", text: "Ping/SSH 가능 + 3306 응답 없음" },
  { label: "재시작 검토", text: "MariaDB active + 3306 응답 없음" },
  { label: "점검 검토", text: "MariaDB 실행 시간 30일 이상" },
  { label: "업무 종료 후 권장", text: "MariaDB 실행 시간 60일 이상" },
];

function ScmEmergencyGuide() {
  return (
    <section className="scm-guide-card" aria-labelledby="scm-guide-title">
      <div>
        <span className="section-kicker">Decision Guide</span>
        <h3 id="scm-guide-title">운영 판단 기준</h3>
        <p>Ping은 되지만 3306 포트가 응답하지 않는 상황을 우선 확인합니다.</p>
      </div>
      <div className="scm-decision-list">
        {DECISION_RULES.map((rule) => (
          <div className="scm-decision-item" key={rule.label}>
            <strong>{rule.label}</strong>
            <span>{rule.text}</span>
          </div>
        ))}
      </div>
      <div className="scm-guide-note">
        이번 단계에서는 MariaDB 실제 재시작을 실행하지 않고 dry-run 조건 확인까지만 제공합니다.
      </div>
    </section>
  );
}

export default ScmEmergencyGuide;
