export const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024;

export const ALLOWED_ATTACHMENT_EXTENSIONS = [
  "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp",
  "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "zip",
];

export const ATTACHMENT_ACCEPT = ALLOWED_ATTACHMENT_EXTENSIONS
  .map((extension) => `.${extension}`)
  .join(",");

const BLOCKED_ATTACHMENT_EXTENSIONS = new Set([
  "exe", "msi", "bat", "cmd", "ps1", "sh", "js", "html", "php", "py", "dll",
]);

export function getAttachmentExtension(filename) {
  const parts = String(filename || "").split(".");
  return parts.length > 1 ? parts.pop().toLowerCase() : "";
}

export function validateAttachmentFile(file) {
  if (!file) {
    return "첨부할 파일을 선택해주세요.";
  }
  if (file.size > MAX_ATTACHMENT_SIZE) {
    return "첨부파일은 최대 20MB까지 등록할 수 있습니다.";
  }

  const extensions = String(file.name || "")
    .split(".")
    .slice(1)
    .map((extension) => extension.toLowerCase());
  const extension = extensions[extensions.length - 1] || "";
  if (
    !ALLOWED_ATTACHMENT_EXTENSIONS.includes(extension) ||
    extensions.some((candidate) => BLOCKED_ATTACHMENT_EXTENSIONS.has(candidate))
  ) {
    return "지원하지 않는 파일 형식입니다.";
  }
  return "";
}
