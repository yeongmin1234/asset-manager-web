import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../src/components/online/RecallManagementPage.jsx", import.meta.url), "utf8");
const tab = readFileSync(new URL("../src/components/online/RecallTargetTab.jsx", import.meta.url), "utf8");
const detail = readFileSync(new URL("../src/components/online/RecallTargetDetailModal.jsx", import.meta.url), "utf8");

test("target matching filters stay separate from raw duplicate filters", () => {
  assert.match(tab, /status, match_status: matchStatus/);
  assert.match(tab, /aria-label="리콜 대상 상태"/);
  assert.match(tab, /aria-label="신청 상태"/);
  assert.match(tab, /기존 데이터 매칭 실행/);
  assert.match(page, /getRecallMatchingSummary\(\)/);
});

test("manual match and release require confirmation and expose linked application detail", () => {
  assert.match(detail, /window\.confirm\(`신청 건/);
  assert.match(detail, /window\.confirm\("이 리콜 대상의 신청 매칭을 해제/);
  assert.match(detail, /manualMatchRecallTarget\(targetId, Number\(selectedId\)\)/);
  assert.match(detail, /unmatchRecallTarget\(targetId\)/);
  assert.match(detail, /신청 상세 보기/);
});
