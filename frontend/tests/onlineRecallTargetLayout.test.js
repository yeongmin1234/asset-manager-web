import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const css = readFileSync(new URL("../src/components/online/online.css", import.meta.url), "utf8");

test("only the active main tab uses the blue filled style", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallManagementPage, { currentUser: { role: "admin" } }));
    assert.match(html, /class="online-page online-recall-page"/);
    const nav = html.match(/<nav class="online-recall-tabs"[\s\S]*?<\/nav>/)?.[0] || "";
    assert.equal((nav.match(/class="active"/g) || []).length, 1);
    assert.match(css, /\.online-recall-tabs button\.active\s*\{[^}]*background:\s*#2563eb;[^}]*color:\s*#fff;/);
    assert.match(css, /\.online-recall-tabs button:not\(\.active\):hover/);
    assert.match(css, /\.online-recall-page \.online-recall-tabs button \{ background: #fff !important; color: #334155 !important; font-size: 0\.96rem;/);
    assert.match(css, /\.online-recall-page \.online-recall-tabs button\.active \{ background: #2563eb !important; color: #fff !important;/);
  } finally { await vite.close(); }
});

test("target summary, compact filters and list-first batch subtabs render", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTargetTab } = await vite.ssrLoadModule("/src/components/online/RecallTargetTab.jsx");
    const { RecallTargetProgressCards, RecallTargetQualityCards, RecallChannelProgress, RecallStageProgress } = await vite.ssrLoadModule("/src/components/online/RecallTargetOverview.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallTargetTab, { pageSize: 20, onPageSizeChange() {} }));
    const progress = renderToStaticMarkup(React.createElement(RecallTargetProgressCards, { summary: { total_count: 20, received_count: 5, remaining_count: 15, in_progress_count: 2, shipped_count: 1 } }));
    assert.equal((progress.match(/class="online-target-progress-card"/g) || []).length, 5);
    assert.match(progress, /25\.0%/);
    const quality = renderToStaticMarkup(React.createElement(RecallTargetQualityCards, { summary: { normal_count: 18, duplicate_count: 1, review_count: 1 } }));
    assert.equal((quality.match(/class="online-target-quality-card"/g) || []).length, 3);
    const stages = renderToStaticMarkup(React.createElement(RecallStageProgress, { summary: { total_count: 20, received_count: 5, in_progress_count: 2, order_count: 1, shipped_count: 1 } }));
    assert.match(stages, /SCM 발주/);
    const channels = renderToStaticMarkup(React.createElement(RecallChannelProgress, { channels: [] }));
    assert.match(channels, /등록된 판매채널이 없습니다/);
    assert.match(css, /\.online-target-progress-cards\s*\{[^}]*repeat\(5,/);
    assert.match(css, /\.online-recall-page \.online-target-progress-card strong \{ font-size: 1\.63rem;/);
    assert.match(css, /\.online-recall-page \.online-target-subtabs button\.active \{ background: #eff6ff !important;[^}]*color: #1d4ed8 !important;/);
    assert.match(css, /\.online-recall-page \.online-target-table td \{ font-size: 1\.07rem;/);
    assert.match(html, /aria-label="리콜 대상 검색"/);
    assert.match(html, /aria-label="리콜 대상 상태"/);
    assert.match(html, /aria-label="신청 상태"/);
    assert.match(html, /페이지당 표시/);
    assert.match(html, /리콜 대상 목록<\/button>/);
    assert.match(html, /업로드 Batch 이력<\/button>/);
    assert.doesNotMatch(html, /aria-label="리콜 대상 업로드 이력"/);
  } finally { await vite.close(); }
});
