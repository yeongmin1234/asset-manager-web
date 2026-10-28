const apiBase = (import.meta.env?.VITE_SCM_API_BASE_URL || "/api/v1").replace(/\/$/, "");
if (apiBase !== "/api/v1") throw new Error("invalid_scm_api_base_url");

export async function authRequest(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, credentials: "include", cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers } });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event("scm-session-expired"));
    const error = new Error("auth_request_failed"); error.status = response.status; throw error;
  }
  return (await response.json()).data;
}

export const login = (username, password) => authRequest("/auth/login", {
  method: "POST", body: JSON.stringify({ username, password }),
});

export const restoreSession = async () => {
  const response = await fetch(`${apiBase}/auth/me`, { credentials: "include", cache: "no-store" });
  if (!response.ok) return null;
  const result = await response.json();
  return result?.ok && result.data ? {
    ...result.data,
    accountType: result.data.account_type,
    account: result.data.subject,
  } : null;
};

export const logout = async () => {
  return authRequest("/auth/logout", { method: "POST" });
};
