import React, { useEffect, useRef } from "react";
import { toScmInnerPath, toScmSitePath } from "./scmRoutes.js";
import "../../styles/scm-site.css";

export default function ScmSiteLayout({ currentUser, path, onNavigateHome, onLogout, onNavigatePath }) {
  const frameRef = useRef(null);
  const innerPath = toScmInnerPath(path);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame?.contentWindow) return;
    try {
      const nextHash = `#${innerPath}`;
      if (frame.contentWindow.location.hash !== nextHash) {
        frame.contentWindow.location.hash = nextHash;
      }
    } catch {
      // The frame's load handler applies the path once the local SCM document is ready.
    }
  }, [innerPath]);

  useEffect(() => {
    const receiveNavigation = (event) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      if (event.data?.type !== "scm-site:navigate" || typeof event.data.path !== "string") return;
      if (!event.data.path.startsWith("/") || event.data.path.startsWith("//")) return;
      onNavigatePath(toScmSitePath(event.data.path));
    };
    window.addEventListener("message", receiveNavigation);
    return () => window.removeEventListener("message", receiveNavigation);
  }, [onNavigatePath]);

  const syncFramePath = () => {
    const frame = frameRef.current;
    if (!frame?.contentWindow) return;
    const nextHash = `#${innerPath}`;
    if (frame.contentWindow.location.hash !== nextHash) frame.contentWindow.location.hash = nextHash;
  };

  return (
    <div className="scm-site-shell">
      <header className="scm-site-header">
        <strong className="scm-site-brand">The Limo &amp; SCM</strong>
        <div className="scm-site-actions">
          <span className="scm-site-sample">샘플 데이터</span>
          <span className="scm-site-user">{currentUser?.name} <small>{currentUser?.role === "admin" ? "관리자" : "일반 사용자"}</small></span>
          <button type="button" onClick={onNavigateHome}>← 시스템 선택</button>
          <button type="button" onClick={onLogout}>로그아웃</button>
        </div>
      </header>
      <iframe
        ref={frameRef}
        className="scm-site-frame"
        title="The Limo SCM"
        src={`/scm-preview/index.html#${innerPath}`}
        onLoad={syncFramePath}
        referrerPolicy="same-origin"
      />
    </div>
  );
}
