export function formatPhoneForDisplay(value) {
  const original = value === null || value === undefined ? "" : String(value);
  const digits = original.replace(/\D/g, "");
  return digits.length === 11
    ? `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
    : original;
}

export const RECALL_STATUS_OPTIONS = [
  { value: "APPLICATION_RECEIVED", label: "접수 완료" },
  { value: "IN_PROGRESS", label: "진행중" },
  { value: "REVIEW_REQUIRED", label: "확인 필요" },
  { value: "STOPPED", label: "중지" },
];

export const RECALL_FILTER_STATUS_OPTIONS = [
  ...RECALL_STATUS_OPTIONS,
  { value: "SHIPPED", label: "발송 완료" },
];

export function displayRecallStatus(value) {
  return RECALL_FILTER_STATUS_OPTIONS.find((option) => option.value === value)?.label || value || "-";
}

const REVIEW_REASON_LABELS = {
  PHONE_INVALID: "연락처 형식 확인 필요",
  APPLICATION_DATE_INVALID: "신청일자 확인 필요",
  PICKUP_DATE_INVALID: "회수 일자 확인 필요",
  QUANTITY_INVALID: "수량 확인 필요",
  ADDRESS_CHECK: "주소 확인 필요",
  SERIAL_CHECK: "시리얼번호 확인 필요",
  MANUAL_REVIEW: "수동 확인 필요",
};

export function displayRecallReviewReasons(codes) {
  if (!Array.isArray(codes) || codes.length === 0) return "-";
  return [...new Set(codes.map((code) => REVIEW_REASON_LABELS[code] || "기타 확인 필요"))].join(" · ");
}

export function recallStatusClass(value) {
  if (value === "IN_PROGRESS") return "online-recall-status-progress";
  if (value === "REVIEW_REQUIRED") return "online-recall-status-review";
  if (value === "STOPPED") return "online-recall-status-stopped";
  if (value === "SHIPPED") return "online-recall-status-shipped";
  return "online-recall-status-received";
}

export function isRecallBulkSelectable(value) {
  return value === "APPLICATION_RECEIVED" || value === "IN_PROGRESS";
}

export function recallTabSelectsAllRows(tab) {
  return tab === "all" || tab === "applications";
}

export function nextRecallBulkStatus(statuses) {
  if (!statuses.length || !statuses.every((status) => status === statuses[0])) return null;
  if (statuses[0] === "APPLICATION_RECEIVED") return "IN_PROGRESS";
  if (statuses[0] === "IN_PROGRESS") return "SHIPPED";
  return null;
}

export function recallManualTargets(currentStatus) {
  const transitions = {
    APPLICATION_RECEIVED: ["IN_PROGRESS", "REVIEW_REQUIRED", "STOPPED"],
    IN_PROGRESS: ["REVIEW_REQUIRED", "STOPPED"],
    REVIEW_REQUIRED: ["APPLICATION_RECEIVED", "STOPPED"],
    STOPPED: ["APPLICATION_RECEIVED", "REVIEW_REQUIRED"],
  };
  return RECALL_STATUS_OPTIONS.filter((option) => (transitions[currentStatus] || []).includes(option.value));
}

export function formatRecallDate(value) {
  return value ? String(value).slice(0, 10) : "-";
}

export function formatRecallDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "-";
}
