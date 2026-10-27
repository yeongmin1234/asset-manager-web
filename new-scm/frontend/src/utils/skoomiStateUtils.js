const DEFAULT_STATUS = Object.freeze({
  state: "default",
  message: "안녕하세요. 이카운트 품목과 재고를 찾아드릴게요.",
});

const errorStatus = (error, apiConfigured) => {
  if (!apiConfigured) {
    return { state: "error", message: "이카운트 연결 설정을 확인해주세요." };
  }
  if ([412, 429].includes(Number(error?.status))) {
    return { state: "error", message: "이카운트 호출이 잠시 제한됐어요. 잠시 후 다시 조회해주세요." };
  }
  if ([401, 403].includes(Number(error?.status)) || error?.code === "AUTH_EXPIRED") {
    return { state: "error", message: "로그인이 만료됐어요. 다시 로그인해주세요." };
  }
  return { state: "error", message: "조회 중 문제가 발생했어요. 잠시 후 다시 시도해주세요." };
};

export function getSkoomiState({
  isLoading = false,
  error = null,
  response = null,
  apiConfigured = true,
} = {}) {
  if (error || !apiConfigured) return errorStatus(error, apiConfigured);
  if (isLoading) return { state: "searching", message: "이카운트 재고를 확인하고 있어요." };
  if (!response) return DEFAULT_STATUS;

  const type = response.data?.type;
  const items = response.data?.items;
  const warehouses = response.data?.warehouses;

  if (type === "item_candidates") {
    return Array.isArray(items) && items.length
      ? { state: "guide", message: "비슷한 품목이 있어요. 조회할 품목을 선택해주세요." }
      : { state: "empty", message: "조건에 맞는 품목을 찾지 못했어요." };
  }
  if (type === "inventory_result") {
    return Array.isArray(warehouses) && warehouses.length === 0
      ? { state: "empty", message: "조건에 맞는 결과가 없어요." }
      : { state: "success", message: "재고 조회가 완료됐어요." };
  }
  if (type === "unsupported" || type === "help" || response.intent === "unsupported" || response.intent === "help") {
    return { state: "guide", message: "품목명, 품목코드 또는 창고별 재고로 질문해주세요." };
  }
  if (response.success === false) return errorStatus(null, apiConfigured);
  return { state: "guide", message: "품목명, 품목코드 또는 창고별 재고로 질문해주세요." };
}
