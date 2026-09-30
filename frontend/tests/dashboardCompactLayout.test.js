import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const css = readFileSync(new URL("../src/styles/app.css", import.meta.url), "utf8");

test("dashboard shows hero, four summary cards and recent history without inventory or AI widgets", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: DashboardPage } = await vite.ssrLoadModule("/src/components/DashboardPage.jsx");
    const html = renderToStaticMarkup(React.createElement(DashboardPage, { currentUser: { role: "admin" }, onNavigate() {} }));
    assert.equal((html.match(/class="dashboard-summary-card dashboard-summary-card-/g) || []).length, 4);
    assert.ok(html.indexOf("안녕하세요, 관리자님!") < html.indexOf("공지사항") && html.indexOf("공지사항") < html.indexOf("최근 변경 이력"));
    assert.doesNotMatch(html, /재고 조회 결과|AI 업무 도우미|inventory-result-panel|ai-assistant-card|dashboard-work-grid/);
    assert.match(html, /class="primary-action"[^>]*>빠른 등록<\/button>/);
    assert.equal((html.match(/class="secondary-button"/g) || []).length >= 4, true);
    assert.match(css, /\.dashboard-page \.dashboard-quick-actions \.secondary-button \{ background: #fff !important;/);
    assert.match(css, /\.dashboard-page \.dashboard-summary-card \{[^}]*height: 100%;[^}]*min-height: 184px;/);
    assert.match(css, /\.dashboard-page \.dashboard-summary-notices li span \{ font-size: 0\.86rem;/);
  } finally { await vite.close(); }
});
