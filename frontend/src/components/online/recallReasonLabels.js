export const RECALL_REASON_LABELS = {
  CUSTOMER_NAME_MISSING: "고객명 확인 필요",
  PHONE_RAW_MISSING: "연락처 확인 필요",
  ADDRESS_MISSING: "주소 확인 필요",
  PHONE_CHECK: "연락처 형식 확인 필요",
  PHONE_INVALID: "연락처 형식 확인 필요",
  ADDRESS_CHECK: "주소 확인 필요",
  SERIAL_CHECK: "시리얼번호 확인 필요",
  DATE_CHECK: "구매일 확인 필요",
  DATE_INVALID: "구매일 확인 필요",
  ORDER_NO_CHECK: "주문번호 확인 필요",
  MULTIPLE_SERIAL_MATCH: "동일 시리얼번호 다건 확인 필요",
  MULTIPLE_PHONE_MATCH: "동일 연락처 다건 확인 필요",
  SERIAL_PHONE_CONFLICT: "시리얼번호와 연락처 매칭 결과가 다름",
  APPLICATION_ALREADY_MATCHED: "이미 다른 신청 건과 연결됨",
  DUPLICATE_APPLICATION: "중복 신청 건 확인 필요",
  VALUE_TOO_LONG: "입력값 길이 확인 필요",
  EMPTY_OR_UNUSABLE: "빈 행 또는 입력값 확인 필요",
  PHONE: "연락처 중복 확인 필요",
  SERIAL: "시리얼번호 중복 확인 필요",
  ORDER_NO: "주문번호 중복 확인 필요",
  PHONE_AND_SERIAL: "연락처·시리얼번호 중복 확인 필요",
  MULTIPLE: "여러 항목 중복 확인 필요",
  APPLICATION_DATE_INVALID: "신청일자 확인 필요",
  PICKUP_DATE_INVALID: "회수 일자 확인 필요",
  QUANTITY_INVALID: "수량 확인 필요",
  MANUAL_REVIEW: "수동 확인 필요",
};

const unknownCodes = new Set();

export function formatRecallReasons(value) {
  const codes = (Array.isArray(value) ? value : [value])
    .flatMap((entry) => String(entry ?? "").split(/[,;|·]/))
    .map((code) => code.trim())
    .filter(Boolean);
  if (!codes.length) return "-";
  return [...new Set(codes.map((code) => {
    if (Object.prototype.hasOwnProperty.call(RECALL_REASON_LABELS, code)) return RECALL_REASON_LABELS[code];
    if (!unknownCodes.has(code)) {
      unknownCodes.add(code);
      console.warn("Unknown recall reason code:", code);
    }
    return "확인 필요";
  }))].join(" · ");
}
