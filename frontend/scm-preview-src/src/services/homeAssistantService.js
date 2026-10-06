import { getAccessToken, notifyAuthExpired } from "./authSession";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function authHeaders() {
  const token = getAccessToken();
  return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function request(path, options = {}) {
  if (!API_BASE_URL) throw new Error("백엔드 API 연결 환경변수가 설정되지 않았습니다.");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: { ...authHeaders(), ...options.headers } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error?.message || "요청을 처리하지 못했습니다.");
    error.status = response.status;
    error.code = body?.error?.code || body?.code || "";
    if (response.status === 401) notifyAuthExpired();
    throw error;
  }
  return body;
}

export const homeAssistantApiConfigured = Boolean(API_BASE_URL);
export const chatAssistant = (message, context) => request("/api/ai/chat", { method: "POST", body: JSON.stringify({ message, context }) });
export const searchECountItems = (query = "") => request(`/api/ai/items?q=${encodeURIComponent(query)}`);
export const getECountInventory = (itemCode, refresh = false) => request(`/api/ai/items/${encodeURIComponent(itemCode)}/inventory?refresh=${refresh}`);
export const getVipCustomerStatus = () => request("/api/home/vip-customer-status");
