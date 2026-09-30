import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../src/components/online/RecallManagementPage.jsx", import.meta.url), "utf8");
const targetModal = readFileSync(new URL("../src/components/online/RecallTargetUploadModal.jsx", import.meta.url), "utf8");
const applicationModal = readFileSync(new URL("../src/components/online/RecallUploadModal.jsx", import.meta.url), "utf8");
const targetTab = readFileSync(new URL("../src/components/online/RecallTargetTab.jsx", import.meta.url), "utf8");

test("raw targets and application uploads use separate flows", () => {
  assert.match(page, /리콜 신청 데이터 등록/);
  assert.match(page, /<RecallTargetUploadModal/);
  assert.match(page, /<RecallUploadModal mode=\{uploadMode\}/);
  assert.match(targetModal, /previewRecallTargetExcel\(file\)/);
  assert.match(targetModal, /commitRecallTargetExcel\(file\)/);
  assert.match(applicationModal, /previewRecallApplicationExcel\(file\)/);
});

test("target tab precedes application tabs and includes filters, paging and batch history", () => {
  assert.ok(page.indexOf('changeTab("targets")') < page.indexOf('changeTab("all")'));
  assert.match(targetTab, /getRecallTargetSummary/);
  assert.match(targetTab, /getRecallTargetBatches/);
  assert.match(targetTab, /RecallPageSizeSelect/);
  assert.match(targetTab, /고객명, 연락처, 주문번호, 시리얼번호/);
  assert.match(targetTab, /업로드 Batch 이력/);
});
