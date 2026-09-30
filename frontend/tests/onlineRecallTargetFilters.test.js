import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const source = readFileSync(new URL("../src/components/online/RecallTargetTab.jsx", import.meta.url), "utf8");

test("target status, channel and matching selects apply immediately while search waits for submit", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallTargetTab } = await vite.ssrLoadModule("/src/components/online/RecallTargetTab.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallTargetTab, { pageSize: 20, onPageSizeChange() {} }));
    for (const label of ["리콜 대상 상태", "판매 채널", "신청 상태", "페이지당 표시 건수"]) {
      assert.match(html, new RegExp(`aria-label="${label}"`));
    }
    assert.match(source, /setStatus\(event\.target\.value\); setPage\(1\)/);
    assert.match(source, /setSalesChannel\(event\.target\.value\); setPage\(1\)/);
    assert.match(source, /setMatchStatus\(event\.target\.value\); setPage\(1\)/);
    assert.match(source, /setAppliedKeyword\(keyword\.trim\(\)\)/);
    assert.match(source, /setSalesChannel\(""\); setMatchStatus\(""\); setPage\(1\); setListRefresh/);
  } finally { await vite.close(); }
});

test("older list and statistics responses cannot overwrite the latest refresh", () => {
  assert.match(source, /const requestId = \+\+listRequestId\.current/);
  assert.match(source, /requestId === listRequestId\.current/);
  assert.match(source, /listRequestId\.current \+= 1/);
  assert.match(source, /const requestId = \+\+statsRequestId\.current/);
  assert.match(source, /requestId !== statsRequestId\.current/);
  assert.match(source, /\[refreshKey, localRefresh\]/);
  assert.match(source, /sales_channel: salesChannel/);
});
