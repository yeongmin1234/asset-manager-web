import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("page size offers four values, defaults to 20, and persists valid choices", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  const { default: RecallPageSizeSelect, readRecallPageSize, saveRecallPageSize } = await vite.ssrLoadModule("/src/components/online/RecallPageSizeSelect.jsx");
  const previousWindow = globalThis.window;
  const values = new Map();
  globalThis.window = { localStorage: {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  } };
  try {
    assert.equal(readRecallPageSize(), 20);
    for (const size of [10, 20, 50, 100]) {
      saveRecallPageSize(size);
      assert.equal(readRecallPageSize(), size);
      const html = renderToStaticMarkup(React.createElement(RecallPageSizeSelect, { value: size, onChange() {} }));
      assert.match(html, /페이지당 표시/);
      assert.match(html, new RegExp(`<option value="${size}" selected="">${size}건</option>`));
    }
    saveRecallPageSize(50);
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const restored = renderToStaticMarkup(React.createElement(RecallManagementPage, { currentUser: { role: "admin" } }));
    assert.match(restored, /<option value="50" selected="">50건<\/option>/);
    saveRecallPageSize(30);
    assert.equal(readRecallPageSize(), 50);
    values.set("onlineRecall.pageSize", "invalid");
    assert.equal(readRecallPageSize(), 20);
  } finally {
    globalThis.window = previousWindow;
    await vite.close();
  }
});

test("all-list action row and SCM toolbar place page size between count and action", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { RecallBulkBar } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const { default: RecallOrderTab } = await vite.ssrLoadModule("/src/components/online/RecallOrderTab.jsx");
    const bar = renderToStaticMarkup(React.createElement(RecallBulkBar, {
      selectedCount: 0, nextStatus: null, disabled: false, isBulkUpdating: false,
      onChange() {}, pageSize: 50, onPageSizeChange() {},
    }));
    assert.ok(bar.indexOf("현재 페이지 선택 0건") < bar.indexOf("페이지당 표시"));
    assert.ok(bar.indexOf("페이지당 표시") < bar.indexOf("다음 단계로 변경 (0)"));
    const duplicates = renderToStaticMarkup(React.createElement(RecallBulkBar, {
      showBulkAction: false, pageSize: 100, onPageSizeChange() {},
    }));
    assert.match(duplicates, /페이지당 표시/);
    assert.doesNotMatch(duplicates, /다음 단계로 변경/);
    const orders = renderToStaticMarkup(React.createElement(RecallOrderTab, { pageSize: 10, onPageSizeChange() {} }));
    assert.ok(orders.indexOf("선택 0건") < orders.indexOf("페이지당 표시"));
    assert.ok(orders.indexOf("페이지당 표시") < orders.indexOf("SCM 발주 Excel 생성"));
  } finally {
    await vite.close();
  }
});
