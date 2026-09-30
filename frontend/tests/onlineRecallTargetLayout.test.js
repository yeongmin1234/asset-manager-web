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
    const nav = html.match(/<nav class="online-recall-tabs"[\s\S]*?<\/nav>/)?.[0] || "";
    assert.equal((nav.match(/class="active"/g) || []).length, 1);
    assert.match(css, /\.online-recall-tabs button\.active\s*\{[^}]*background:\s*#2563eb;[^}]*color:\s*#fff;/);
    assert.match(css, /\.online-recall-tabs button:not\(\.active\):hover/);
  } finally { await vite.close(); }
});

test("target summary, compact filters and list-first batch subtabs render", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTargetTab } = await vite.ssrLoadModule("/src/components/online/RecallTargetTab.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallTargetTab, { pageSize: 20, onPageSizeChange() {} }));
    const summary = html.match(/<section class="online-order-summary online-target-summary online-target-raw-summary"[\s\S]*?<\/section>/)?.[0] || "";
    assert.equal((summary.match(/data-tone=/g) || []).length, 4);
    for (const tone of ["total", "normal", "duplicate", "review"]) assert.match(summary, new RegExp(`data-tone="${tone}"`));
    assert.match(css, /\.online-target-summary\s*\{\s*grid-template-columns:\s*repeat\(4,/);
    assert.match(html, /aria-label="리콜 대상 검색"/);
    assert.match(html, /aria-label="리콜 대상 상태"/);
    assert.match(html, /aria-label="신청 상태"/);
    assert.match(html, /페이지당 표시/);
    assert.match(html, /리콜 대상 목록<\/button>/);
    assert.match(html, /업로드 Batch 이력<\/button>/);
    assert.doesNotMatch(html, /aria-label="리콜 대상 업로드 이력"/);
  } finally { await vite.close(); }
});
