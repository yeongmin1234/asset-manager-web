import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("duplicate registration filter, row badge and detail remain separate from duplicate review", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallFilters } = await vite.ssrLoadModule("/src/components/online/RecallFilters.jsx");
    const { default: RecallTable } = await vite.ssrLoadModule("/src/components/online/RecallTable.jsx");
    const { RecallDuplicateRegistrationDetails } = await vite.ssrLoadModule("/src/components/online/RecallDetailModal.jsx");
    const props = { values: { keyword: "", status: "" }, onChange() {}, onSearch() {}, onReset() {} };
    const visibleFilter = renderToStaticMarkup(React.createElement(RecallFilters, { ...props, showRegistrationFilter: true }));
    const hiddenFilter = renderToStaticMarkup(React.createElement(RecallFilters, props));
    assert.match(visibleFilter, /value="DUPLICATE_REGISTRATION">중복 등록/);
    assert.doesNotMatch(hiddenFilter, /DUPLICATE_REGISTRATION/);
    const item = { id: 1, customer_name: "고객", current_status: "IN_PROGRESS", duplicate_flag: false,
      duplicate_registration_attempt: true, duplicate_registration_count: 3,
      last_duplicate_registration_at: "2026-09-30T10:30:00", last_duplicate_registration_batch_id: 9 };
    const row = renderToStaticMarkup(React.createElement(RecallTable, { items: [item], selectedIds: new Set(),
      onToggleSelection() {}, onTogglePage() {}, onOpenDetail() {} }));
    assert.match(row, /진행중/);
    assert.match(row, /중복 등록 시도: 3회/);
    assert.doesNotMatch(row, /중복 확인<\/span>/);
    const detail = renderToStaticMarkup(React.createElement(RecallDuplicateRegistrationDetails, { detail: item }));
    assert.match(detail, /중복 등록 시도 횟수<\/dt><dd>3회/);
    assert.match(detail, /마지막 중복 등록 시각<\/dt><dd>2026-09-30 10:30/);
    assert.match(detail, /마지막 업로드 Batch<\/dt><dd>#9/);
    assert.equal(renderToStaticMarkup(React.createElement(RecallDuplicateRegistrationDetails, { detail: {} })), "");
  } finally { await vite.close(); }
});
