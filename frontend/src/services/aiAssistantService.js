import {
  ApiError,
  analyzeInventory,
  getLowStockInventory,
  postAiChat,
  saveAiInventoryContext,
  searchInventory,
} from "../api/client.js";

const INVENTORY_INTENTS = new Set([
  "inventory_search", "inventory_low_stock", "inventory_item_code", "inventory_refresh",
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

export async function sendAiAssistantMessage(message) {
  try {
    return await postAiChat(message);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) throw new Error("로그인이 만료되었습니다.");
      if (error.status === 403) throw new Error("업무 도우미를 사용할 권한이 없습니다.");
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
  return String(intent || "").startsWith("inventory_context_");
}

export function isInventoryAnalysisIntent(intent) {
  return INVENTORY_ANALYSIS_INTENTS.has(intent);
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
  const params = getInventoryQuery(aiResponse, originalQuestion);
  if (!params.itemCode && !params.keyword && aiResponse.intent !== "inventory_low_stock") {
    throw new Error("조회할 품목명 또는 품목코드를 함께 입력해주세요.");
  }
  const isLowStock = aiResponse.intent === "inventory_low_stock"
    || (aiResponse.intent === "inventory_refresh" && aiResponse.data?.source_intent === "inventory_low_stock");
  const inventoryResponse = isLowStock
    ? await getLowStockInventory({ ...params, threshold: aiResponse.data?.threshold || 10 })
    : await searchInventory(params);
  return {
    inventoryResponse,
    answer: buildInventoryAnswer(inventoryResponse),
  };
}

export async function rememberInventoryContext({ aiResponse, query, inventoryResponse }) {
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
