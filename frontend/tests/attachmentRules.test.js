import assert from "node:assert/strict";
import test from "node:test";

import {
  ALLOWED_ATTACHMENT_EXTENSIONS,
  ATTACHMENT_ACCEPT,
  MAX_ATTACHMENT_SIZE,
  validateAttachmentFile,
} from "../src/utils/attachmentRules.js";

const file = (name, size = 1) => ({ name, size });

test("안내된 확장자와 대문자 확장자를 허용한다", () => {
  const expected = [
    "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "zip",
  ];
  assert.deepEqual(ALLOWED_ATTACHMENT_EXTENSIONS, expected);
  assert.equal(ATTACHMENT_ACCEPT, expected.map((value) => `.${value}`).join(","));
  for (const extension of expected) {
    assert.equal(validateAttachmentFile(file(`업무 설명.${extension.toUpperCase()}`)), "");
  }
});

test("파일 없음, 용량 초과, 미지원 및 실행 이중 확장자를 구분한다", () => {
  assert.equal(validateAttachmentFile(null), "첨부할 파일을 선택해주세요.");
  assert.equal(validateAttachmentFile(file("ok.pdf", MAX_ATTACHMENT_SIZE)), "");
  assert.equal(
    validateAttachmentFile(file("large.pdf", MAX_ATTACHMENT_SIZE + 1)),
    "첨부파일은 최대 20MB까지 등록할 수 있습니다.",
  );
  assert.equal(validateAttachmentFile(file("data.csv")), "지원하지 않는 파일 형식입니다.");
  assert.equal(validateAttachmentFile(file("document.pdf.exe")), "지원하지 않는 파일 형식입니다.");
  assert.equal(validateAttachmentFile(file("document.exe.pdf")), "지원하지 않는 파일 형식입니다.");
});
