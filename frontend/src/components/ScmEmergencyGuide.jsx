import React from "react";

const GUIDE_STEPS = [
  "1단계: Ping/SSH 연결 확인",
  "2단계: MariaDB 상태 확인",
  "3단계: 3306 포트 확인",
  "4단계: MariaDB 재시작",
  "5단계: 그래도 안 되면 웹서버 상태 확인",
];

function ScmEmergencyGuide() {
  return (
    <section className="scm-guide-card" aria-labelledby="scm-guide-title">
      <div>
        <span className="section-kicker">Emergency Guide</span>
        <h3 id="scm-guide-title">장애 조치 가이드</h3>
        <p>SCM 장애가 MariaDB freeze인지 먼저 좁혀서 확인합니다.</p>
      </div>
      <ol>
        {GUIDE_STEPS.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <div className="scm-guide-note">
        이번 단계에서는 MariaDB 실제 재시작을 실행하지 않고 dry-run 조건 확인까지만 제공합니다.
      </div>
    </section>
  );
}

export default ScmEmergencyGuide;
