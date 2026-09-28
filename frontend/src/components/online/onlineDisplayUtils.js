export function formatPhoneForDisplay(value) {
  const original = value === null || value === undefined ? "" : String(value);
  const digits = original.replace(/\D/g, "");
  return digits.length === 11
    ? `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`
    : original;
}

export function displayRecallStatus(value) {
  return value === "APPLICATION_RECEIVED" ? "접수 완료" : value || "-";
}
