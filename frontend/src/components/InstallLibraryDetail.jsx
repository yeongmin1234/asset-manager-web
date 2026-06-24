import React from "react";

function InstallLibraryDetail({ item = null, onClose }) {
  if (!item) {
    return null;
  }

  return (
    <div className="modal-backdrop install-library-modal-backdrop" role="presentation">
      <section className="install-library-detail-modal" role="dialog" aria-modal="true" aria-labelledby="install-library-detail-title">
        <div className="install-library-modal-header">
          <div>
            <span className="section-kicker">Install Guide</span>
            <h3 id="install-library-detail-title">{item.title}</h3>
            <p>{item.description || "등록된 설명이 없습니다."}</p>
          </div>
          <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="install-library-detail-grid">
          <section>
            <h4>설치 방법</h4>
            <p>{item.install_guide || "등록된 설치 방법이 없습니다."}</p>
          </section>
          <section className="install-library-warning-box">
            <h4>주의사항</h4>
            <p>{item.caution_note || "등록된 주의사항이 없습니다."}</p>
          </section>
        </div>
      </section>
    </div>
  );
}

export default InstallLibraryDetail;
