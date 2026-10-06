const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function headers() {
  const token = sessionStorage.getItem("access_token");
  return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

async function request(path, options = {}) {
  if (!API_BASE_URL) throw new Error("마켓 API 연결 환경변수가 설정되지 않았습니다.");
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: { ...headers(), ...options.headers } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(response.status === 409 ? (body.message || body.detail || "이미 등록된 마켓입니다.") : "마켓 처리 중 오류가 발생했습니다.");
    error.status = response.status;
    throw error;
  }
  return body;
}

export const marketplaceApiConfigured = Boolean(API_BASE_URL);
export const getMarketplaces = () => request("/marketplaces");
export const getActiveMarketplaces = () => request("/marketplaces?status=active");
export const createMarketplace = (data) => request("/marketplaces", { method: "POST", body: JSON.stringify(data) });
export const activateMarketplace = (id) => request(`/marketplaces/${id}/activate`, { method: "POST" });
export const deactivateMarketplace = (id) => request(`/marketplaces/${id}/deactivate`, { method: "POST" });
export const getMarketplaceSalesUsage = async (id) => {
  const result = await request(`/sales?marketplace_id=${encodeURIComponent(id)}&size=1`);
  return Number(result.total || 0) > 0;
};
