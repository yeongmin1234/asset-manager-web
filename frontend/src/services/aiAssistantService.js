import {
  ApiError,
  analyzeInventory,
  analyzeInventoryChange,
  getInventoryAlerts,
  getInventoryAlertSummary,
  postAiChat,
  saveAiInventoryContext,
  searchInventory,
} from "../api/client.js";
export { buildInventoryCardData } from "../utils/inventoryDisplayUtils.js";

const INVENTORY_INTENTS = new Set([
  "inventory_search", "inventory_item_code", "inventory_refresh", "inventory_item_warehouse_search",
]);
const INVENTORY_ANALYSIS_INTENTS = new Set([
  "inventory_compare",
  "inventory_sort",
  "inventory_filter",
  "inventory_low_stock",
  "inventory_min",
  "inventory_max",
  "inventory_zero",
  "inventory_negative",
]);
const INVENTORY_CHANGE_INTENTS = new Set([
  "inventory_change_summary",
  "inventory_change_compare",
  "inventory_increased",
  "inventory_decreased",
  "inventory_largest_increase",
  "inventory_largest_decrease",
  "inventory_history_compare",
]);
const INVENTORY_ALERT_INTENTS = new Set([
  "inventory_alert_summary", "inventory_out_of_stock", "inventory_alert_negative",
  "inventory_rapid_decrease", "inventory_alert_low_stock",
]);

export async function sendAiAssistantMessage(message, context = null) {
  try {
    return await postAiChat(message, context);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) throw new Error("로그인이 만료되었습니다.");
      if (error.status === 403) throw new Error("업무 도우미를 사용할 권한이 없습니다.");
      if (error.status === 429) throw new Error(error.message || "이카운트 요청 제한으로 잠시 후 다시 조회할 수 있습니다.");
      if (error.status === 504) throw new Error("재고 조회 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.");
      if (error.status === 502 || error.status === 503) throw new Error("현재 재고 정보를 불러올 수 없습니다.");
      if (error.status >= 500) throw new Error("질문 처리 중 오류가 발생했습니다.");
      if (!error.status) throw new Error("업무 도우미 서버에 연결할 수 없습니다.");
      throw new Error(error.message || "질문을 처리할 수 없습니다.");
    }
    throw new Error("업무 도우미 서버에 연결할 수 없습니다.");
  }
}

export function isInventoryIntent(intent) {
  return INVENTORY_INTENTS.has(intent);
}

export function isInventoryContextIntent(intent) {
  return new Set([
    "inventory_warehouse_filter", "inventory_show_all_warehouses", "inventory_other_warehouses",
    "inventory_context_warehouses",
  ]).has(String(intent || ""));
}

export function buildConversationContext(inventoryResponse, intent = "inventory_search") {
  const items = Array.isArray(inventoryResponse?.items) ? inventoryResponse.items : [];
  if (items.length !== 1) return null;
  const item = items[0];
  return {
    selected_item_code: item.item_code || null,
    selected_item_name: item.item_name || null,
    unit: item.unit || null,
    size: item.size || null,
    last_intent: intent,
    searched_at: new Date().toISOString(),
    last_warehouse_filter: null,
    last_warehouse_keyword: null,
    pending_warehouse_keyword: null,
    pending_warehouse_expression: null,
    search_keyword: null,
    product_candidates: [],
    inventory_result: {
      total_quantity: item.total_quantity ?? null,
      warehouses: Array.isArray(item.warehouses) ? item.warehouses : [],
    },
  };
}

export function filterInventoryForWarehouse(inventoryResponse, warehouseKeyword) {
  const items = Array.isArray(inventoryResponse?.items) ? inventoryResponse.items : [];
  if (items.length !== 1 || !warehouseKeyword) {
    return { inventoryResponse, context: buildConversationContext(inventoryResponse), answer: null, analysis: null };
  }
  const item = items[0];
  const allWarehouses = Array.isArray(item.warehouses) ? item.warehouses : [];
  const normalizedKeyword = normalizeWarehouseText(warehouseKeyword);
  const rawKeyword = normalizeWarehouseSpacing(warehouseKeyword);
  const exact = allWarehouses.filter((warehouse) => (
    normalizeWarehouseSpacing(warehouse.warehouse_name) === rawKeyword
  ));
  const matched = exact.length ? exact : allWarehouses.filter((warehouse) => (
    normalizeWarehouseText(warehouse.warehouse_name).includes(normalizedKeyword)
  ));
  const filteredQuantity = sumDecimalQuantities(matched.map((warehouse) => warehouse.quantity));
  const filteredItem = { ...item, total_quantity: String(filteredQuantity), warehouses: matched };
  const nextContext = buildConversationContext(inventoryResponse, "inventory_item_warehouse_search");
  if (nextContext) {
    nextContext.last_warehouse_filter = warehouseKeyword;
    nextContext.last_warehouse_keyword = warehouseKeyword;
    nextContext.pending_warehouse_keyword = null;
  }
  const name = item.item_name || item.item_code;
  const answer = matched.length
    ? `${name}의 ${warehouseKeyword} 관련 창고 재고는 총 ${formatQuantity(filteredQuantity)}개입니다.\n${matched.map((warehouse) => `• ${warehouse.warehouse_name || warehouse.warehouse_code || "창고"}: ${formatQuantity(warehouse.quantity)}개`).join("\n")}`
    : `'${name}'의 재고 결과에서 '${warehouseKeyword}'와 일치하는 창고를 찾지 못했습니다.`;
  return {
    inventoryResponse: { ...inventoryResponse, items: [filteredItem] },
    context: nextContext,
    answer,
    analysis: {
      type: "inventory_warehouse_filter", label: `창고 필터: ${warehouseKeyword}`,
      warehouse_keyword: warehouseKeyword, match_count: matched.length,
      filtered_quantity: filteredQuantity, total_quantity: item.total_quantity,
    },
  };
}

function normalizeWarehouseText(value) {
  return normalizeWarehouseSpacing(value).replace(/창고$/, "").trim();
}

function normalizeWarehouseSpacing(value) {
  return String(value || "").trim().toLocaleLowerCase().replace(/\s+/g, " ");
}

function sumDecimalQuantities(values) {
  const parsed = values.map((value) => {
    const match = String(value ?? "0").replace(/,/g, "").trim().match(/^([+-]?)(\d+)(?:\.(\d+))?$/);
    return match ? { negative: match[1] === "-", whole: match[2], fraction: match[3] || "" } : null;
  }).filter(Boolean);
  const scale = parsed.reduce((maximum, value) => Math.max(maximum, value.fraction.length), 0);
  const total = parsed.reduce((sum, value) => {
    const digits = BigInt(`${value.whole}${value.fraction.padEnd(scale, "0")}` || "0");
    return sum + (value.negative ? -digits : digits);
  }, 0n);
  const negative = total < 0n;
  const absolute = (negative ? -total : total).toString().padStart(scale + 1, "0");
  if (!scale) return `${negative ? "-" : ""}${absolute}`;
  const whole = absolute.slice(0, -scale) || "0";
  const fraction = absolute.slice(-scale).replace(/0+$/, "");
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

export function isInventoryAnalysisIntent(intent) {
  return INVENTORY_ANALYSIS_INTENTS.has(intent);
}

export function isInventoryChangeIntent(intent) {
  return INVENTORY_CHANGE_INTENTS.has(intent);
}

export function isInventoryAlertIntent(intent) { return INVENTORY_ALERT_INTENTS.has(intent); }

export function isInventoryRecommendationIntent(intent) {
  return intent === "inventory_recommendation";
}

export async function fetchRecommendedInventoryItem(item) {
  const inventoryResponse = await searchInventory({ itemCode: item.item_code, limit: 1 });
  return { inventoryResponse, answer: buildInventoryAnswer(inventoryResponse) };
}

export async function fetchInventoryAlertsForAi(aiResponse) {
  const types = {
    inventory_out_of_stock: "OUT_OF_STOCK", inventory_alert_negative: "NEGATIVE_STOCK",
    inventory_rapid_decrease: "RAPID_DECREASE", inventory_alert_low_stock: "LOW_STOCK",
  };
  const response = aiResponse.intent === "inventory_alert_summary"
    ? await getInventoryAlertSummary() : await getInventoryAlerts({ alertType: types[aiResponse.intent] });
  const total = response.active_total ?? response.total ?? response.items?.length ?? 0;
  const answer = aiResponse.intent === "inventory_alert_summary"
    ? `현재 확인이 필요한 재고 경고는 ${total}건입니다.\n\n품절 ${response.out_of_stock || 0}건\n부족 재고 ${response.low_stock || 0}건\n음수 재고 ${response.negative_stock || 0}건\n급감 품목 ${response.rapid_decrease || 0}건\n\n상세 결과는 왼쪽 패널에서 확인할 수 있습니다.`
    : `현재 조건에 해당하는 재고 경고는 ${total}건입니다. 상세 결과는 왼쪽 패널에서 확인할 수 있습니다.`;
  return { inventoryResponse: response, answer };
}

export async function fetchInventoryChangeForAi(aiResponse) {
  const isLargest = aiResponse.intent === "inventory_largest_increase"
    || aiResponse.intent === "inventory_largest_decrease";
  const response = await analyzeInventoryChange({
    itemCode: aiResponse.data?.item_code,
    keyword: aiResponse.data?.keyword,
    direction: aiResponse.data?.direction || "all",
    extreme: aiResponse.intent === "inventory_largest_increase"
      ? "largest_increase"
      : aiResponse.intent === "inventory_largest_decrease" ? "largest_decrease" : undefined,
    mode: aiResponse.data?.mode || "latest_previous",
    todayOnly: aiResponse.data?.today_only || false,
    limit: isLargest ? 10 : 200,
  }, aiResponse.intent === "inventory_change_summary");
  return {
    inventoryResponse: response,
    answer: response.answer || response.message,
  };
}

export async function fetchInventoryAnalysisForAi(aiResponse) {
  const response = await analyzeInventory({
    intent: aiResponse.intent,
    queries: aiResponse.data?.items,
    direction: aiResponse.data?.direction,
    comparison: aiResponse.data?.comparison,
    threshold: aiResponse.data?.threshold,
  });
  return {
    inventoryResponse: response,
    answer: response.answer || response.message,
  };
}

export async function fetchInventoryForAi(aiResponse, originalQuestion) {
  if (aiResponse.data?.inventory_response) {
    return {
      inventoryResponse: aiResponse.data.inventory_response,
      answer: aiResponse.message || buildInventoryAnswer(aiResponse.data.inventory_response),
    };
  }
  const params = getInventoryQuery(aiResponse, originalQuestion);
  if (!params.itemCode && !params.keyword && aiResponse.intent !== "inventory_low_stock") {
    throw new Error("조회할 품목명 또는 품목코드를 함께 입력해주세요.");
  }
  const isLowStock = aiResponse.intent === "inventory_low_stock"
    || (aiResponse.intent === "inventory_refresh" && aiResponse.data?.source_intent === "inventory_low_stock");
  if (isLowStock) {
    const answer = "현재 부족 재고 전체 조회 기능은 안정화를 위해 일시 중지되었습니다.\n품목명 또는 품목코드로 재고를 조회해주세요.";
    return {
      inventoryResponse: {
        success: true, authenticated: true, total: 0, items: [], message: answer,
        response_time_ms: 0, analysis: { type: "inventory_low_stock", disabled: true },
      },
      answer,
    };
  }
  const inventoryResponse = await searchInventory(params);
  return {
    inventoryResponse,
    answer: buildInventoryAnswer(inventoryResponse),
  };
}

export async function rememberInventoryContext({ aiResponse, query, inventoryResponse }) {
  if (aiResponse.data?.inventory_response) return;
  const items = Array.isArray(inventoryResponse?.items) ? inventoryResponse.items : [];
  if (!items.length) return;
  await saveAiInventoryContext({
    intent: aiResponse.intent === "inventory_refresh"
      ? (aiResponse.data?.source_intent || "inventory_search")
      : aiResponse.intent,
    query,
    items,
    threshold: aiResponse.data?.threshold ?? null,
    searched_at: new Date().toISOString(),
    selected_item_code: items[0]?.item_code || null,
  });
}

function getInventoryQuery(aiResponse, originalQuestion) {
  const explicitCode = aiResponse.data?.item_code || extractItemCode(originalQuestion);
  if (explicitCode) return { itemCode: explicitCode, keyword: undefined };
  const parsedKeyword = cleanInventoryKeyword(
    aiResponse.data?.keyword || extractInventoryKeyword(originalQuestion),
  );
  return { keyword: parsedKeyword || undefined, itemCode: undefined };
}

function extractItemCode(question) {
  const labeled = question.match(/품목\s*코드\s*[:#]?\s*([a-z0-9._-]+)/i);
  if (labeled) return labeled[1].toUpperCase();
  const leading = question.trim().match(/^([a-z0-9][a-z0-9._-]*)\s+(?:재고|창고)/i);
  return leading ? leading[1].toUpperCase() : "";
}

function extractInventoryKeyword(question) {
  return cleanInventoryKeyword(question
    .replace(/재고\s*\d+\s*개?\s*(?:이하|미만)/g, "")
    .replace(/(?:창고별\s*)?재고(?:량)?/g, "")
    .replace(/(?:알려줘|보여줘|조회|확인|품목|상품|해줘)/g, "")
    .trim());
}

function cleanInventoryKeyword(value) {
  return String(value || "")
    .replace(/창고별/g, "")
    .replace(/(?:알려줘|보여줘|조회|확인|해줘)/g, "")
    .trim();
}

function buildInventoryAnswer(response) {
  const items = Array.isArray(response?.items) ? response.items : [];
  if (!items.length) {
    return "검색 조건에 맞는 재고가 없습니다.\n품목명 또는 품목코드를 다시 확인해 주세요.";
  }
  if (items.length > 1) {
    return `검색된 품목은 ${items.length}개입니다.\n재고 상세는 왼쪽 재고 조회 결과에서 확인할 수 있습니다.`;
  }
  const item = items[0];
  const warehouses = (item.warehouses || [])
    .map((warehouse) => `${warehouse.warehouse_name || warehouse.warehouse_code || "창고"} ${formatQuantity(warehouse.quantity)}개`)
    .join(", ");
  return `${item.item_name || item.item_code}의 현재 총재고는 ${formatQuantity(item.total_quantity)}개입니다.${warehouses ? `\n${warehouses}입니다.` : ""}\n왼쪽 재고 조회 결과에서 상세 내용을 확인할 수 있습니다.`;
}

function formatQuantity(value) {
  const raw = String(value ?? "");
  return raw.includes(".") ? raw.replace(/0+$/, "").replace(/\.$/, "") : raw;
}
