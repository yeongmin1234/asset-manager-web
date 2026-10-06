import { clearAccessToken, getAccessToken, storeAccessToken } from "./authSession";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const LOCAL_HOSTNAMES = new Set(["127.0.0.1", "localhost"]);

export function isFrontendDevMode() {
  return import.meta.env.VITE_FRONTEND_DEV_MODE === "true"
    && LOCAL_HOSTNAMES.has(window.location.hostname);
}

async function parseResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.error?.message || body?.detail || "인증 요청을 처리하지 못했습니다.");
    error.status = response.status;
    error.code = body?.error?.code || "";
    throw error;
  }
  return body;
}

export async function login(username, password, remember = false) {
  if (!API_BASE_URL) throw new Error("백엔드 API 연결 설정을 확인해주세요.");
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const result = await parseResponse(response);
  if (!result.access_token) throw new Error("로그인 토큰을 발급받지 못했습니다.");
  storeAccessToken(result.access_token, remember);
  return result;
}

export async function devLogin() {
  if (!isFrontendDevMode()) return null;
  if (!API_BASE_URL) throw new Error("백엔드 API 연결 설정을 확인해주세요.");
  const response = await fetch(`${API_BASE_URL}/api/auth/dev-login`, { method: "POST" });
  const result = await parseResponse(response);
  if (!result.access_token) throw new Error("개발용 로그인 토큰을 발급받지 못했습니다.");
  storeAccessToken(result.access_token, false);
  return result;
}

export async function restoreSession() {
  const token = getAccessToken();
  if (!token || !API_BASE_URL) return null;
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return await parseResponse(response);
  } catch (error) {
    if (error.status === 401 || error.status === 403) clearAccessToken();
    return null;
  }
}

export function logout() {
  clearAccessToken();
}
