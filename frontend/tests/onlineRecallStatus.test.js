import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { nextRecallBulkStatus, recallManualTargets } from "../src/components/online/onlineDisplayUtils.js";

test("bulk action offers only the next step for a uniform selection", () => {
  assert.equal(nextRecallBulkStatus([]), null);
  assert.equal(nextRecallBulkStatus(["APPLICATION_RECEIVED", "APPLICATION_RECEIVED"]), "IN_PROGRESS");
  assert.equal(nextRecallBulkStatus(["IN_PROGRESS", "IN_PROGRESS"]), "SHIPPED");
  assert.equal(nextRecallBulkStatus(["APPLICATION_RECEIVED", "IN_PROGRESS"]), null);
  assert.equal(nextRecallBulkStatus(["SHIPPED"]), null);
});

test("detail editor excludes reverse transitions after progress and shipping", () => {
  assert.equal(recallManualTargets("IN_PROGRESS").some((option) => option.value === "APPLICATION_RECEIVED"), false);
  assert.deepEqual(recallManualTargets("SHIPPED"), []);
});

test("recall list keeps Excel order, centered cells and eligible checkboxes", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTable } = await vite.ssrLoadModule("/src/components/online/RecallTable.jsx");
    const item = {
      id: 1, application_date: "2026-09-22", quantity: 1, customer_name: "신성아",
      phone_original: "01099810165", address: "원효로 138", memo: "방문 전 연락",
      current_status: "APPLICATION_RECEIVED", serial_number: null, lot_number: null,
    };
    const html = renderToStaticMarkup(React.createElement(RecallTable, {
      items: [item], selectedIds: new Set([1]), onToggleSelection() {}, onTogglePage() {}, onOpenDetail() {},
    }));
    assert.ok(html.indexOf("메모</th>") < html.indexOf("현재 상태</th>"));
    assert.ok(html.indexOf("현재 상태</th>") < html.indexOf("시리얼번호</th>"));
    assert.match(html, /010-9981-0165/);
    assert.match(html, /신성아 상태 변경 선택/);
    assert.match(html, /checked=""/);
    assert.match(html, /online-recall-long-cell/);
  } finally {
    await vite.close();
  }
});

test("bulk controls show the allowed action and disable mixed selections", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { RecallBulkBar } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const render = (props) => renderToStaticMarkup(React.createElement(RecallBulkBar, { onChange() {}, isBulkUpdating: false, disabled: false, ...props }));
    assert.match(render({ selectedCount: 2, nextStatus: "IN_PROGRESS" }), /진행중으로 변경 \(2\)/);
    assert.match(render({ selectedCount: 2, nextStatus: "SHIPPED" }), /발송완료로 변경 \(2\)/);
    const mixed = render({ selectedCount: 2, nextStatus: null });
    assert.match(mixed, /같은 상태의 항목만 선택해야 합니다/);
    assert.match(mixed, /disabled=""/);
    assert.match(render({ selectedCount: 0, nextStatus: null }), /disabled=""/);
  } finally {
    await vite.close();
  }
});

test("detail shows recovery only for shipped and summary keeps five status tones", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { RecallDetailStatusActions } = await vite.ssrLoadModule("/src/components/online/RecallDetailModal.jsx");
    const { default: RecallSummaryCards } = await vite.ssrLoadModule("/src/components/online/RecallSummaryCards.jsx");
    const props = {
      status: "SHIPPED", reason: "", recoveryReason: "", saving: false,
      onStatusChange() {}, onReasonChange() {}, onRecoveryReasonChange() {}, onSubmit() {}, onRecover() {},
    };
    const shipped = renderToStaticMarkup(React.createElement(RecallDetailStatusActions, { ...props, detail: { current_status: "SHIPPED" } }));
    assert.match(shipped, /접수완료로 되돌리기/);
    assert.match(shipped, /복구 사유/);
    assert.match(shipped, /required=""/);
    for (const currentStatus of ["APPLICATION_RECEIVED", "IN_PROGRESS", "REVIEW_REQUIRED", "STOPPED"]) {
      const other = renderToStaticMarkup(React.createElement(RecallDetailStatusActions, { ...props, status: currentStatus, detail: { current_status: currentStatus } }));
      assert.doesNotMatch(other, /접수완료로 되돌리기/);
      assert.match(other, /변경 상태/);
    }

    const cards = renderToStaticMarkup(React.createElement(RecallSummaryCards, { summary: {
      total_count: 20, received_count: 11, remaining_count: 11, in_progress_count: 5, shipped_count: 4,
    } }));
    for (const tone of ["total", "received", "remaining", "progress", "shipped"]) {
      assert.match(cards, new RegExp(`data-tone="${tone}"`));
    }
    assert.match(cards, /발송완료<\/span><strong>4<\/strong>/);
  } finally {
    await vite.close();
  }
});
