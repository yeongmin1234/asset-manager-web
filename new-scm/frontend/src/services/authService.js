const apiBase = (import.meta.env.VITE_SCM_API_BASE_URL || "/api/v1").replace(/\/$/, "");

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
  await fetch(`${apiBase}/auth/logout`, { method: "POST", credentials: "include" });
};
