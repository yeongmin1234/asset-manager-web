import { formatRecallReasons } from "./recallReasonLabels.js";

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
  { value: "DUPLICATE_REGISTRATION", label: "중복 등록" },
];

export function displayRecallStatus(value) {
  return RECALL_FILTER_STATUS_OPTIONS.find((option) => option.value === value)?.label || value || "-";
}

export function displayRecallReviewReasons(codes) {
  return formatRecallReasons(codes);
}

export const RECALL_MATCH_METHOD_LABELS = {
  PHONE: "연락처",
  SERIAL: "시리얼번호",
  ORDER_NO: "주문번호",
  MANUAL: "수동 매칭",
};

export const RECALL_MATCH_STATUS_LABELS = {
  MATCHED: "신청 완료",
  UNMATCHED: "미접수",
  REVIEW: "확인 필요",
  REVIEW_REQUIRED: "확인 필요",
};

const RECALL_TARGET_PROGRESS_LABELS = {
  ...RECALL_MATCH_STATUS_LABELS,
  APPLICATION_RECEIVED: "접수 완료",
  IN_PROGRESS: "진행중",
  SHIPPED: "발송 완료",
  STOPPED: "중지",
};

export function displayRecallMatchMethod(value) {
  return value ? RECALL_MATCH_METHOD_LABELS[value] || "확인 필요" : "-";
}

export function displayRecallMatchStatus(value) {
  return value ? RECALL_MATCH_STATUS_LABELS[value] || "확인 필요" : "-";
}

export function recallMatchStatusClass(value) {
  return value === "MATCHED" || value === "UNMATCHED" ? value : "REVIEW";
}

export function displayRecallTargetProgress(applicationStatus, matchStatus) {
  const value = applicationStatus || matchStatus;
  return value ? RECALL_TARGET_PROGRESS_LABELS[value] || "확인 필요" : "-";
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
