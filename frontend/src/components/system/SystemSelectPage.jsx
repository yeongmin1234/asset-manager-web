import React from "react";
import "../../styles/system-select.css";

const SYSTEMS = [
  {
    id: "dashboard",
    icon: "▣",
    title: "자산관리 시스템",
    description: "자산 관리, 온라인 TEAM, 리콜, 발주 등 사내 업무를 통합 관리합니다.",
  },
  {
    id: "scm-app",
    icon: "▦",
    title: "SCM 시스템",
    description: "매장관리, 고객상담, 고객관리, A/S, 판매와 물류 업무를 관리합니다.",
  },
];

export default function SystemSelectPage({ currentUser, canOpenAssets, canOpenScm, onSelect, onLogout }) {
  const access = { dashboard: canOpenAssets, "scm-app": canOpenScm };

  return (
    <main className="system-select-page">
      <header className="system-select-header">
        <strong>The Limo &amp;</strong>
        <span>{currentUser?.name}님, 사용할 시스템을 선택해주세요.</span>
      </header>
      <div className="system-select-grid">
        {SYSTEMS.map((system) => {
          const allowed = access[system.id];
          return (
            <button
              key={system.id}
              type="button"
              className="system-select-card"
              disabled={!allowed}
              onClick={() => onSelect(system.id)}
              aria-label={allowed ? `${system.title} 들어가기` : `${system.title} 접근 권한 없음`}
            >
              <span className="system-select-icon" aria-hidden="true">{system.icon}</span>
              <strong>{system.title}</strong>
              <span className="system-select-description">{system.description}</span>
              <span className="system-select-card-footer">{allowed ? "시스템으로 이동 →" : "접근 권한 없음"}</span>
            </button>
          );
        })}
      </div>
      <button className="system-select-logout" type="button" onClick={onLogout}>로그아웃</button>
    </main>
  );
}
