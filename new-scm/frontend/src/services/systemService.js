export async function getSystemStatus() {
  const baseUrl = import.meta.env.VITE_SCM_API_BASE_URL || "/api/v1";
  if (baseUrl !== "/api/v1") throw new Error("invalid_scm_api_base_url");
  const response = await fetch(`${baseUrl}/system/status`, {
    cache: "no-store",
    signal: AbortSignal.timeout(3000),
  });
  if (!response.ok) throw new Error("system_status_unavailable");
  const body = await response.json();
  if (!body.ok || body.data?.service !== "new-scm") {
    throw new Error("unexpected_system_status");
  }
  return body.data;
}
