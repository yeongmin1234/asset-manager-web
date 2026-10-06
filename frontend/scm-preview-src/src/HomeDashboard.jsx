import React, { useState } from "react";
import AiAssistantPanel from "./AiAssistantPanel";
import VipCustomerPanel from "./VipCustomerPanel";
import { initialNotices } from "./noticeMockData";
import { NoticeDetailModal } from "./NoticeModals";

const summaries = [
  { title: "상담문의", path: "/consultations", items: [["상담접수", "0"], ["회신준비", "0"]] },
  { title: "A/S", path: "/as", items: [["AS접수", "0"], ["수리중", "0"]] },
  { title: "판매", path: "/sales", items: [["판매접수", "0"], ["발주요청", "0"]] },
  { title: "물류", path: "/logistics", items: [["출고인계", "0"], ["발주취소", "0"]] },
];

export default function HomeDashboard({ onNavigate }) {
  const [notices, setNotices] = useState(initialNotices);
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const notice = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2500);
  };
  const openNotice = (item) => {
    const updated = { ...item, views: item.views + 1 };
    setNotices((current) => current.map((entry) => entry.id === item.id ? updated : entry));
    setDetail(updated);
  };
  const sortedNotices = [...notices].sort(
    (a, b) => Number(b.pinned) - Number(a.pinned) || b.date.localeCompare(a.date),
  );

  return (
    <section className="home-business-dashboard">
      <div className="home-dashboard-grid">
        <section className="home-work-panel home-notice-panel">
          <h2>사내 공지사항</h2>
          <div className="home-table-scroll">
            <table>
              <thead><tr><th>번호</th><th>등록일시</th><th>제목</th><th>작성자</th><th>읽음</th></tr></thead>
              <tbody>
                {sortedNotices.length ? sortedNotices.map((item) => (
                  <tr key={item.id} className={item.pinned ? "pinned" : ""} onClick={() => openNotice(item)}>
                    <td>{item.no}</td><td>{item.date}</td><td title={item.title}>{item.title}</td>
                    <td>{item.author}</td><td>{item.views}</td>
                  </tr>
                )) : <tr><td className="home-empty" colSpan={5}>등록된 공지사항이 없습니다.</td></tr>}
              </tbody>
            </table>
          </div>
          <footer><button type="button" onClick={() => onNavigate("/notices")}>모두보기</button></footer>
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
      {detail && <NoticeDetailModal notice={detail} onClose={() => setDetail(null)} />}
      {toast && <div className="product-toast">{toast}</div>}
    </section>
  );
}
