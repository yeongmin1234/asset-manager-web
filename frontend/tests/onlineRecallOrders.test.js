import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("Phase 5 order tab keeps compact summary and pending-only selection controls", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const { default: RecallOrderTab } = await vite.ssrLoadModule("/src/components/online/RecallOrderTab.jsx");
    const page = renderToStaticMarkup(React.createElement(RecallManagementPage, { currentUser: { role: "admin" } }));
    const orderTab = renderToStaticMarkup(React.createElement(RecallOrderTab, { isAdmin: true }));
    assert.match(page, /접수 목록/);
    assert.match(page, /주문 대상/);
    assert.match(orderTab, /발주 대기/);
    assert.match(orderTab, /Excel 생성 완료/);
    assert.match(orderTab, /발주 완료/);
    assert.match(orderTab, /SCM 발주 Excel 생성/);
    assert.match(orderTab, /현재 페이지 발주 대기 전체 선택/);
    assert.match(orderTab, /disabled=""/);
  } finally {
    await vite.close();
  }
});
