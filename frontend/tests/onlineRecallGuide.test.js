import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { RECALL_GUIDE_STORAGE_KEY, RECALL_GUIDE_VERSION, saveRecallGuideDismissal, shouldShowRecallGuide } from "../src/components/online/recallGuideStorage.js";

test("guide storage shows on first visit and after ordinary close, hides after opt-out, and returns when cleared or version changes", () => {
  const previousWindow = globalThis.window;
  const values = new Map();
  globalThis.window = { localStorage: {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  } };
  try {
    assert.equal(RECALL_GUIDE_STORAGE_KEY, "recallGuideVersion");
    assert.equal(RECALL_GUIDE_VERSION, "v1");
    assert.equal(shouldShowRecallGuide(), true);
    assert.equal(shouldShowRecallGuide(), true); // Closing without opt-out stores nothing.
    saveRecallGuideDismissal();
    assert.equal(values.get(RECALL_GUIDE_STORAGE_KEY), "v1");
    assert.equal(shouldShowRecallGuide(), false);
    values.set(RECALL_GUIDE_STORAGE_KEY, "v0");
    assert.equal(shouldShowRecallGuide(), true);
    values.delete(RECALL_GUIDE_STORAGE_KEY);
    assert.equal(shouldShowRecallGuide(), true);
  } finally { globalThis.window = previousWindow; }
});

test("guide remains available when browser storage is blocked", () => {
  const previousWindow = globalThis.window;
  globalThis.window = { localStorage: { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } } };
  try {
    assert.equal(shouldShowRecallGuide(), true);
    assert.doesNotThrow(() => saveRecallGuideDismissal());
  } finally { globalThis.window = previousWindow; }
});

test("recall entry selects targets and offers the same six-step guide at any time", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const { default: RecallGuideModal } = await vite.ssrLoadModule("/src/components/online/RecallGuideModal.jsx");
    const page = renderToStaticMarkup(React.createElement(RecallManagementPage, { currentUser: { role: "admin" } }));
    const nav = page.match(/<nav class="online-recall-tabs"[\s\S]*?<\/nav>/)?.[0] || "";
    assert.match(nav, /class="active" aria-current="page"[^>]*>리콜 대상<\/button>/);
    const actions = page.match(/<div class="online-recall-actions">[\s\S]*?<\/div>/)?.[0] || "";
    assert.match(actions, /사용설명서[\s\S]*리콜 신청 데이터 등록[\s\S]*리콜 대상 등록/);
    const guide = renderToStaticMarkup(React.createElement(RecallGuideModal, { onClose() {} }));
    assert.match(guide, /리콜 관리 사용 안내/);
    for (const label of ["리콜 대상 등록", "리콜 신청 데이터 등록", "자동 매칭", "중복 / 확인 필요 검토", "기존 데이터 매칭 실행", "SCM 발주 대상", "업무 흐름", "앞으로 보지 않음"]) {
      assert.match(guide, new RegExp(label));
    }
    assert.match(guide, /시리얼번호 1순위, 연락처 2순위/);
    assert.match(guide, /아직 연결되지 않은 건을 다시 매칭합니다/);
    assert.match(guide, /aria-label="사용 안내 닫기"/);
    assert.equal((guide.match(/<li>/g) || []).length, 6);
    const source = readFileSync(new URL("../src/components/online/RecallManagementPage.jsx", import.meta.url), "utf8");
    assert.match(source, /setGuideOpen\(shouldShowRecallGuide\(\)\)/);
    assert.match(source, /onClick=\{\(\) => setGuideOpen\(true\)\}>사용설명서/);
    assert.match(source, /if \(dontShowAgain\) saveRecallGuideDismissal\(\)/);
  } finally { await vite.close(); }
});
