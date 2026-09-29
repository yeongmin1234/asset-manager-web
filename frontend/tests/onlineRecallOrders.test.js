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
    assert.match(page, /중복 확인/);
    assert.match(page, /SCM 발주 대상/);
    assert.ok(page.indexOf("전체 목록") < page.indexOf("접수 목록"));
    assert.ok(page.indexOf("접수 목록") < page.indexOf("중복 확인"));
    assert.ok(page.indexOf("중복 확인") < page.indexOf("SCM 발주 대상"));
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

test("all-list table marks only duplicate rows and retains review status", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTable } = await vite.ssrLoadModule("/src/components/online/RecallTable.jsx");
    const items = [
      { id: 1, customer_name: "정상", current_status: "APPLICATION_RECEIVED", duplicate_flag: false },
      { id: 2, customer_name: "확인", current_status: "REVIEW_REQUIRED", duplicate_flag: false },
      { id: 3, customer_name: "중복", current_status: "APPLICATION_RECEIVED", duplicate_flag: true },
    ];
    const html = renderToStaticMarkup(React.createElement(RecallTable, {
      items, selectedIds: new Set(), onToggleSelection() {}, onTogglePage() {}, onOpenDetail() {},
    }));
    assert.equal((html.match(/class="online-recall-duplicate-row"/g) || []).length, 1);
    assert.equal((html.match(/online-recall-duplicate-badge/g) || []).length, 1);
    assert.match(html, /online-recall-status-review/);
  } finally {
    await vite.close();
  }
});

test("all-list selects every recall status while delete button follows selection", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTable } = await vite.ssrLoadModule("/src/components/online/RecallTable.jsx");
    const { default: RecallFilters } = await vite.ssrLoadModule("/src/components/online/RecallFilters.jsx");
    const items = [
      { id: 1, customer_name: "정상 고객", current_status: "APPLICATION_RECEIVED" },
      { id: 2, customer_name: "확인 고객", current_status: "REVIEW_REQUIRED" },
      { id: 3, customer_name: "중복 고객", current_status: "APPLICATION_RECEIVED", duplicate_flag: true },
      { id: 4, customer_name: "발송 고객", current_status: "SHIPPED" },
    ];
    const table = renderToStaticMarkup(React.createElement(RecallTable, {
      items, selectAllRows: true, selectedIds: new Set([1, 2, 3, 4]),
      onToggleSelection() {}, onTogglePage() {}, onOpenDetail() {},
    }));
    for (const name of items.map((item) => item.customer_name)) {
      const checkbox = table.match(new RegExp(`<input[^>]*aria-label="${name} 선택"[^>]*>`))?.[0];
      assert.ok(checkbox, `${name} checkbox`);
      assert.doesNotMatch(checkbox, /disabled/);
    }
    assert.match(table, /현재 페이지 전체 선택/);
    const renderFilters = (selectedCount) => renderToStaticMarkup(React.createElement(RecallFilters, {
      values: { keyword: "", status: "" }, onChange() {}, onSearch() {}, onReset() {},
      onDelete() {}, selectedCount, isLoading: false,
    }));
    assert.match(renderFilters(0), /online-recall-delete-button" disabled=""[^>]*>삭제/);
    assert.match(renderFilters(2), /online-recall-delete-button"[^>]*>삭제/);
  } finally {
    await vite.close();
  }
});

test("duplicate review list displays the reference and resolution actions", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallDuplicateReview } = await vite.ssrLoadModule("/src/components/online/RecallDuplicateReview.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallDuplicateReview, {
      items: [{ id: 2, customer_name: "신규 고객", phone_original: "01012345678", serial_number: "S-2",
        duplicate_reason: "PHONE", application_date: "2026-09-29",
        duplicate_reference: { id: 1, customer_name: "기존 고객", phone_original: "010-1234-5678", serial_number: "S-1", application_date: "2026-09-22" } }],
      isLoading: false, error: "", onDetail() {}, onResolved() {},
    }));
    assert.match(html, /연락처/);
    assert.match(html, /기존 접수 정보/);
    assert.match(html, /신규 접수 정보/);
    assert.match(html, /정상 건으로 처리/);
    assert.match(html, /중복 건 유지/);
    assert.match(html, /010-1234-5678/);
  } finally {
    await vite.close();
  }
});
