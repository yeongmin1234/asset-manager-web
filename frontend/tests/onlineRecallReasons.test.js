import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { formatRecallReasons } from "../src/components/online/recallReasonLabels.js";

test("target, duplicate, matching and application review codes share Korean labels", () => {
  assert.equal(formatRecallReasons("CUSTOMER_NAME_MISSING, PHONE_RAW_MISSING|SERIAL_CHECK"),
    "고객명 확인 필요 · 연락처 확인 필요 · 시리얼번호 확인 필요");
  assert.equal(formatRecallReasons(["PHONE", "MULTIPLE_SERIAL_MATCH", "SERIAL_PHONE_CONFLICT"]),
    "연락처 중복 확인 필요 · 동일 시리얼번호 다건 확인 필요 · 시리얼번호와 연락처 매칭 결과가 다름");
  assert.equal(formatRecallReasons("PHONE_INVALID,PHONE_CHECK"), "연락처 형식 확인 필요");
  assert.equal(formatRecallReasons(null), "-");
});

test("unknown codes are hidden from the UI and remain visible in the developer console", () => {
  const warnings = [];
  const previous = console.warn;
  console.warn = (...parts) => warnings.push(parts.join(" "));
  try {
    assert.equal(formatRecallReasons("SERIAL_CHECK, FUTURE_REASON_CODE"), "시리얼번호 확인 필요 · 확인 필요");
    assert.equal(formatRecallReasons("FUTURE_REASON_CODE"), "확인 필요");
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /FUTURE_REASON_CODE/);
  } finally { console.warn = previous; }
});

test("list, preview and detail use the same compact reason text with Korean tooltip", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: RecallReasonText } = await vite.ssrLoadModule("/src/components/online/RecallReasonText.jsx");
    const html = renderToStaticMarkup(React.createElement(RecallReasonText, { reasons: ["SERIAL_CHECK", "MULTIPLE_PHONE_MATCH"] }));
    assert.match(html, /title="시리얼번호 확인 필요 · 동일 연락처 다건 확인 필요"/);
    assert.doesNotMatch(html, /SERIAL_CHECK|MULTIPLE_PHONE_MATCH/);
    for (const filename of ["RecallTargetTab.jsx", "RecallTargetUploadModal.jsx", "RecallTargetDetailModal.jsx"]) {
      const source = readFileSync(new URL(`../src/components/online/${filename}`, import.meta.url), "utf8");
      assert.match(source, /<RecallReasonText reasons=/);
    }
  } finally { await vite.close(); }
});
