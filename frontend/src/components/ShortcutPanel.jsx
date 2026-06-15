import React from "react";

const SHORTCUTS = [
  { id: "quick", title: "빠른 등록", desc: "새 자산 등록", icon: "+" },
  { id: "assets", title: "자산 목록", desc: "목록 조회", icon: "≡" },
  { id: "excel", title: "엑셀 관리", desc: "가져오기/내보내기", icon: "▧" },
  { id: "reports", title: "통계 / 리포트", desc: "현황 보기", icon: "◔" },
];

function ShortcutPanel({ onNavigate }) {
  return (
    <section className="portal-side-card" aria-labelledby="shortcut-title">
      <div className="side-card-heading">
        <h3 id="shortcut-title">바로가기</h3>
      </div>
      <div className="shortcut-list">
        {SHORTCUTS.map((shortcut) => (
          <button
            type="button"
            className="shortcut-item"
            key={shortcut.id}
            onClick={() => onNavigate?.(shortcut.id)}
          >
            <span className="shortcut-icon">{shortcut.icon}</span>
            <span>
              <strong>{shortcut.title}</strong>
              <small>{shortcut.desc}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default ShortcutPanel;
