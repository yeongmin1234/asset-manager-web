export function formatPhoneForDisplay(value) {
  const original = value === null || value === undefined ? "" : String(value);
  const digits = original.replace(/\D/g, "");
  return digits.length === 11
    ? `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
    : original;
}

export const RECALL_STATUS_OPTIONS = [
  { value: "APPLICATION_RECEIVED", label: "접수 완료" },
  { value: "REVIEW_REQUIRED", label: "확인 필요" },
  { value: "STOPPED", label: "중지" },
];

export function displayRecallStatus(value) {
  return RECALL_STATUS_OPTIONS.find((option) => option.value === value)?.label || value || "-";
}

export function recallStatusClass(value) {
  if (value === "REVIEW_REQUIRED") return "online-recall-status-review";
  if (value === "STOPPED") return "online-recall-status-stopped";
  return "online-recall-status-received";
}

export function formatRecallDate(value) {
  return value ? String(value).slice(0, 10) : "-";
}

export function formatRecallDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "-";
}
