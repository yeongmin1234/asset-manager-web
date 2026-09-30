import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const tab = readFileSync(new URL("../src/components/online/RecallTargetTab.jsx", import.meta.url), "utf8");
const modal = readFileSync(new URL("../src/components/online/RecallTargetDeleteModal.jsx", import.meta.url), "utf8");

test("target list starts with disabled delete and page selection checkbox", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTargetTab } = await vite.ssrLoadModule("/src/components/online/RecallTargetTab.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallTargetTab, { pageSize: 10, onPageSizeChange() {} }));
    assert.match(html, /aria-label="현재 페이지 전체 선택"[^>]*disabled/);
    assert.match(html, /class="secondary-button online-recall-delete-button" disabled=""[^>]*>삭제<\/button>/);
    assert.ok(html.indexOf("페이지당 표시") < html.indexOf(">삭제</button>") && html.indexOf(">삭제</button>") < html.indexOf("기존 데이터 매칭 실행"));
  } finally { await vite.close(); }
});

test("selection is page scoped, matched rows can be deleted, and success refreshes counts", () => {
  assert.match(tab, /new Set\(pageIds\)/);
  assert.doesNotMatch(tab, /selectedMatched|blocked=\{/);
  assert.match(tab, /deleteRecallTargets\(\[\.\.\.selectedIds\], reason\)/);
  assert.match(tab, /onTargetsChanged\(\)/);
  assert.match(modal, /삭제된 대상은 리콜 대상 목록과 통계에서 제외됩니다/);
  assert.match(modal, /연결된 신청 데이터와 이력은 유지됩니다/);
  assert.doesNotMatch(modal, /매칭을 해제해주세요/);
  assert.match(modal, /required maxLength=\{255\}/);
});
