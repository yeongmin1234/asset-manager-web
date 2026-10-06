import React from "react";
import "../styles/scm-preview.css";

export default function ScmPreviewPage() {
  return (
    <section className="scm-preview-page" aria-labelledby="scm-preview-title">
      <header className="scm-preview-heading">
        <div>
          <h2 id="scm-preview-title">예비 SCM 미리보기</h2>
          <p>별도 프로젝트의 화면을 샘플 데이터로 확인합니다. 이 화면의 변경은 운영 DB에 저장되지 않습니다.</p>
        </div>
      </header>
      <iframe
        className="scm-preview-frame"
        title="예비 SCM 화면 미리보기"
        src="/scm-preview/index.html#/"
        referrerPolicy="no-referrer"
      />
    </section>
  );
}
