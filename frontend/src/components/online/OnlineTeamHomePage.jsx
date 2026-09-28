import React from "react";
import OnlineFeatureCards from "./OnlineFeatureCards.jsx";
import OnlineSummaryCards from "./OnlineSummaryCards.jsx";
import "./online.css";

function OnlineTeamHomePage({ onNavigate }) {
  return (
    <div className="online-page">
      <div className="portal-screen-heading">
        <h2>온라인 TEAM</h2>
        <p>온라인 업무 현황과 주요 관리 기능을 확인합니다.</p>
      </div>
      <OnlineSummaryCards />
      <OnlineFeatureCards onNavigate={onNavigate} />
    </div>
  );
}

export default OnlineTeamHomePage;
