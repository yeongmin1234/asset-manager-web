import React, { useEffect, useState } from "react";
import AiAssistantPanel from "./AiAssistantPanel";
import VipCustomerPanel from "./VipCustomerPanel";
import { getRecentActivity } from "./services/activityBridge";
import { actionLabels, formatActivityTime, moduleLabels } from "./activityPresentation";

const summaries = [
  { title: "상담문의", path: "/consultations", items: [["상담접수", "0"], ["회신준비", "0"]] },
  { title: "A/S", path: "/as", items: [["AS접수", "0"], ["수리중", "0"]] },
  { title: "판매", path: "/sales", items: [["판매접수", "0"], ["발주요청", "0"]] },
  { title: "물류", path: "/logistics", items: [["출고인계", "0"], ["발주취소", "0"]] },
];

export default function HomeDashboard({ onNavigate }) {
  const [activities, setActivities] = useState([]);
  const [activityError, setActivityError] = useState("");
  const [toast, setToast] = useState("");
  const notice = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2500);
  };
  useEffect(() => {
    let active = true;
    const refresh = () => getRecentActivity().then(
      (result) => { if (active) { setActivities(result.recent_activity || []); setActivityError(""); } },
      (error) => { if (active) setActivityError(error.message); },
    );
    refresh();
    const timer = window.setInterval(refresh, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  return (
    <section className="home-business-dashboard">
      <div className="home-dashboard-grid">
        <section className="home-work-panel home-notice-panel home-activity-panel">
          <h2>최근 작업 기록</h2>
          <div className="home-table-scroll">
            <table>
              <thead><tr><th>시간</th><th>사용자</th><th>작업 내용</th><th>모듈</th><th>작업 유형</th></tr></thead>
              <tbody>
                {activities.length ? activities.map((item) => (
                  <tr key={item.id}>
                    <td>{formatActivityTime(item.created_at)}</td><td>{item.user_name}</td><td title={item.message}>{item.message}</td>
                    <td>{moduleLabels[item.module] || item.module}</td><td>{actionLabels[item.action] || item.action}</td>
                  </tr>
                )) : <tr><td className="home-empty" colSpan={5}>{activityError || "기록된 작업이 없습니다."}</td></tr>}
              </tbody>
            </table>
          </div>
          <footer><button type="button" onClick={() => onNavigate("/activity")}>전체 이력 보기</button></footer>
        </section>
        <div className="home-dashboard-right">
          <VipCustomerPanel />
          <div className="home-summary-cards">
            {summaries.map((card) => (
              <button type="button" key={card.title} onClick={() => onNavigate(card.path)}>
                <strong>{card.title}</strong>
                {card.items.map(([label, value]) => <span key={label}>{label}: <b>{Number(value).toLocaleString()}건</b></span>)}
              </button>
            ))}
          </div>
          <AiAssistantPanel />
        </div>
      </div>
      <section className="home-business-links">
        <h2>업무 사이트 연결</h2>
        <nav>
          {["발뮤다몰 운영자 화면", "발뮤다몰", "발뮤다몰 Facebook", "발뮤다몰 네이버 블로그"].map((label, index) => (
            <React.Fragment key={label}>
              {index > 0 && <span>|</span>}
              <button type="button" onClick={() => notice("프론트 개발 모드에서는 외부 사이트를 열지 않습니다.")}>{label}</button>
            </React.Fragment>
          ))}
        </nav>
      </section>
      {toast && <div className="product-toast">{toast}</div>}
    </section>
  );
}
