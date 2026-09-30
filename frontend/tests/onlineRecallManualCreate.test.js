import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("recall header offers direct registration between guide and Excel registration", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallManagementPage, { currentUser: { role: "admin" } }));
    const actions = html.match(/<div class="online-recall-actions">[\s\S]*?<\/div>/)?.[0] || "";
    assert.match(actions, /사용설명서[\s\S]*직접 등록[\s\S]*리콜 신청 데이터 등록[\s\S]*리콜 대상 등록/);
    const modal = readFileSync(new URL("../src/components/online/RecallManualCreateModal.jsx", import.meta.url), "utf8");
    assert.match(modal, /리콜 신청 직접 등록/);
    assert.match(modal, /createRecallApplicationManually\(values\)/);
    for (const field of ["customer_name", "phone_original", "address", "serial_number", "lot_number", "pickup_agreement", "pickup_date", "replacement_shipping_agreement"]) {
      assert.match(modal, new RegExp(field));
    }
  } finally { await vite.close(); }
});

test("progressed recall deletion requires explicit history confirmation", () => {
  const source = readFileSync(new URL("../src/components/online/RecallDeleteModal.jsx", import.meta.url), "utf8");
  assert.match(source, /progressedCount > 0 && !confirmed/);
  assert.match(source, /발주\/발송 이력이 보존됨을 확인했습니다/);
  assert.match(source, /삭제 사유/);
});

test("manual registration keeps required labels inline and gives memo a full-height textarea", () => {
  const modal = readFileSync(new URL("../src/components/online/RecallManualCreateModal.jsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../src/components/online/online.css", import.meta.url), "utf8");
  assert.match(modal, /<span className="online-recall-manual-label">\{label\}\{required && <span className="online-recall-manual-required"/);
  assert.match(modal, /key === "memo" \? <textarea value=\{values\[key\]\}/);
  assert.match(modal, /address", "주소지"[\s\S]*?memo", "메모"[\s\S]*?serial_number", "시리얼번호"/);
  assert.match(css, /\.online-recall-manual-grid \{[^}]*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /\.online-recall-manual-label \{ white-space: nowrap; \}/);
  assert.match(css, /\.online-recall-manual-grid textarea \{ min-height: 104px; overflow-y: auto; resize: vertical; \}/);
  assert.match(modal, /createRecallApplicationManually\(values\)/);
});
