import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { displayRecallMatchMethod, displayRecallMatchStatus, displayRecallTargetProgress } from "../src/components/online/onlineDisplayUtils.js";

test("recall target match and progress codes use safe Korean labels", () => {
  for (const [code, label] of Object.entries({ PHONE: "연락처", SERIAL: "시리얼번호", ORDER_NO: "주문번호", MANUAL: "수동 매칭" })) {
    assert.equal(displayRecallMatchMethod(code), label);
  }
  for (const [code, label] of Object.entries({ MATCHED: "신청 완료", UNMATCHED: "미접수", REVIEW: "확인 필요", REVIEW_REQUIRED: "확인 필요" })) {
    assert.equal(displayRecallMatchStatus(code), label);
    assert.equal(displayRecallTargetProgress(code), label);
  }
  assert.equal(displayRecallTargetProgress("APPLICATION_RECEIVED", "MATCHED"), "접수 완료");
  assert.equal(displayRecallTargetProgress("IN_PROGRESS", "MATCHED"), "진행중");
  assert.equal(displayRecallTargetProgress("SHIPPED", "MATCHED"), "발송 완료");
  assert.equal(displayRecallTargetProgress(null, "UNMATCHED"), "미접수");
  assert.equal(displayRecallMatchMethod(null), "-");
  assert.equal(displayRecallMatchMethod("NEW_CODE"), "확인 필요");
  assert.equal(displayRecallMatchStatus("NEW_CODE"), "확인 필요");
  assert.equal(displayRecallTargetProgress("NEW_CODE"), "확인 필요");
});

test("target list and detail reuse the same labels without exposing raw codes", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { RecallTargetMatchCells } = await vite.ssrLoadModule("/src/components/online/RecallTargetTab.jsx");
    const html = renderToStaticMarkup(React.createElement("tr", null,
      React.createElement(RecallTargetMatchCells, { item: { match_status: "MATCHED", match_method: "PHONE", application_status: "IN_PROGRESS" } })));
    assert.match(html, /신청 완료/);
    assert.match(html, /연락처/);
    assert.match(html, /진행중/);
    assert.doesNotMatch(html, />PHONE<|>MATCHED<|>IN_PROGRESS</);
    const unknown = renderToStaticMarkup(React.createElement("tr", null,
      React.createElement(RecallTargetMatchCells, { item: { match_status: "NEW", match_method: "NEW", application_status: "NEW" } })));
    assert.doesNotMatch(unknown, />NEW</);
    const detail = readFileSync(new URL("../src/components/online/RecallTargetDetailModal.jsx", import.meta.url), "utf8");
    assert.match(detail, /displayRecallMatchStatus\(target\.match_status\)/);
    assert.match(detail, /displayRecallMatchMethod\(target\.match_method\)/);
    assert.match(detail, /displayRecallTargetProgress\(detail\.application\?\.current_status, target\.match_status\)/);
  } finally { await vite.close(); }
});
