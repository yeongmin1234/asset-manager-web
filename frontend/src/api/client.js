const DEFAULT_API_PORT = "8010";
const AUTH_TOKEN_STORAGE_KEY = "assetManager.accessToken";

function getApiBaseUrl() {
  const browserLocation =
    typeof window !== "undefined" ? window.location : undefined;

  return resolveApiBaseUrl(browserLocation);
}

export function resolveApiBaseUrl(browserLocation) {
  const browserHostname = browserLocation?.hostname || "";
  if (!browserHostname) {
    return "";
  }
  const protocol = browserLocation.protocol || "http:";
  return `${protocol}//${browserHostname}:${DEFAULT_API_PORT}`;
}

const API_BASE_URL = getApiBaseUrl();
const REQUEST_TIMEOUT_MS = 6000;

export class ApiError extends Error {
  constructor(message, { status, detail, url, method } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.url = url;
    this.method = method;
  }
}

async function request(path, options = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  if (options.query) {
    Object.entries(options.query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  const fetchOptions = {
    method: options.method || "GET",
    signal: controller.signal,
    headers: {
      Accept: "application/json",
      ...getAuthHeaders(),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  };

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (error) {
    logApiFailure({ error, method: fetchOptions.method, path, url });
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
      method: fetchOptions.method,
      url: url.toString(),
    });
  } finally {
    window.clearTimeout(timeoutId);
  }

  const contentType = response.headers.get("content-type") || "";
  let data = null;
  try {
    data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  } catch {
    data = null;
  }

  if (!response.ok) {
    handleUnauthorized(response);
    logApiFailure({ data, method: fetchOptions.method, path, response, url });
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
      method: fetchOptions.method,
      url: url.toString(),
    });
  }

  return data;
}

async function requestBlob(path, options = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  if (options.query) {
    Object.entries(options.query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    });
  }

  let response;
  try {
    response = await fetch(url, {
      method: options.method || "GET",
      signal: controller.signal,
      headers: {
        Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ...getAuthHeaders(),
        ...options.headers,
      },
    });
  } catch (error) {
    logApiFailure({ error, method: options.method || "GET", path, url });
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
      method: options.method || "GET",
      url: url.toString(),
    });
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    handleUnauthorized(response);
    const contentType = response.headers.get("content-type") || "";
    let data = null;
    try {
      data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
    } catch {
      data = null;
    }
    logApiFailure({ data, method: options.method || "GET", path, response, url });
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
      method: options.method || "GET",
      url: url.toString(),
    });
  }

  return {
    blob: await response.blob(),
    filename: getDownloadFilename(response.headers.get("content-disposition")),
  };
}

async function requestFormData(path, formData, options = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, {
      method: options.method || "POST",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...getAuthHeaders(),
        ...options.headers,
      },
      body: formData,
    });
  } catch (error) {
    logApiFailure({ error, method: options.method || "POST", path, url });
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
      method: options.method || "POST",
      url: url.toString(),
    });
  } finally {
    window.clearTimeout(timeoutId);
  }

  const contentType = response.headers.get("content-type") || "";
  let data = null;
  try {
    data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  } catch {
    data = null;
  }

  if (!response.ok) {
    handleUnauthorized(response);
    logApiFailure({ data, method: options.method || "POST", path, response, url });
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
      method: options.method || "POST",
      url: url.toString(),
    });
  }

  return data;
}

function getErrorMessage(data, status) {
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => item.msg).join(" ");
  }
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  if (typeof data?.message === "string") {
    return data.message;
  }
  if (typeof data === "string" && data) {
    return data;
  }
  return `API 요청에 실패했습니다. (${status})`;
}

function logApiFailure({ data, error, method, path, response, url }) {
  if (typeof console === "undefined") {
    return;
  }

  console.error("[AssetManager API] request failed", {
    apiBaseUrl: API_BASE_URL,
    method,
    path,
    requestUrl: url.toString(),
    status: response?.status,
    statusText: response?.statusText,
    errorName: error?.name,
    errorMessage: error?.message,
    response: data,
  });
}

export async function getHealth() {
  return request("/health");
}

export async function login(username, password) {
  const result = await request("/auth/login", {
    method: "POST",
    body: { username, password },
  });
  saveAuthToken(result.access_token);
  return result;
}

export async function getCurrentUser() {
  return request("/auth/me");
}

export function getAuthToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
}

export function saveAuthToken(token) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  }
}

export function clearAuthToken() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

export async function getDatabaseHealth() {
  return request("/health/db");
}

export async function getNetworkStatus() {
  return request("/network/status", { timeoutMs: 30000 });
}

export async function getScmServerStatus() {
  return request("/server-operations/scm/status", { timeoutMs: 15000 });
}

export async function dryRunScmMariaDbRestart(payload) {
  return request("/server-operations/scm/mariadb/restart/dry-run", {
    method: "POST",
    body: payload,
    timeoutMs: 10000,
  });
}

export async function restartScmMariaDb(payload) {
  return request("/server-operations/scm/mariadb/restart", {
    method: "POST",
    body: payload,
    timeoutMs: 30000,
  });
}

export async function getNetworkCredentials(filters = {}) {
  return normalizeCollection(await request("/network-credentials", { query: filters }));
}

export async function getNetworkCredentialSummary() {
  return request("/network-credentials/summary");
}

export async function createNetworkCredential(credential) {
  return request("/network-credentials", {
    method: "POST",
    body: credential,
  });
}

export async function updateNetworkCredential(credentialId, credential) {
  return request(`/network-credentials/${credentialId}`, {
    method: "PUT",
    body: credential,
  });
}

export async function deleteNetworkCredential(credentialId) {
  return request(`/network-credentials/${credentialId}`, {
    method: "DELETE",
  });
}

export async function revealNetworkCredentialPassword(credentialId, adminPassword) {
  return request(`/network-credentials/${credentialId}/reveal-password`, {
    method: "POST",
    body: { admin_password: adminPassword },
    timeoutMs: 8000,
  });
}

export async function getInstallFiles(filters = {}) {
  return request("/install-files", { query: filters });
}

export async function getInstallFile(fileId) {
  return request(`/install-files/${fileId}`);
}

export async function getInstallFileSummary() {
  return request("/install-files/summary");
}

export async function createInstallFile(payload) {
  return requestFormData("/install-files", buildInstallFileFormData(payload), {
    timeoutMs: 60000,
  });
}

export async function updateInstallFile(fileId, payload) {
  return requestFormData(`/install-files/${fileId}`, buildInstallFileFormData(payload), {
    method: "PUT",
    timeoutMs: 60000,
  });
}

export async function deleteInstallFile(fileId, adminPassword) {
  return request(`/install-files/${fileId}`, {
    method: "DELETE",
    body: { admin_password: adminPassword },
  });
}

export async function downloadInstallFile(fileId) {
  return requestBlob(`/install-files/${fileId}/download`, {
    timeoutMs: 120000,
  });
}

export async function pingVisitor() {
  return request("/visitors/ping", {
    method: "POST",
  });
}

export async function getVisitorsSummary() {
  return request("/visitors/summary");
}

export async function getCategories() {
  return normalizeCollection(await request("/categories"));
}

export async function createCategory(category) {
  return request("/categories", {
    method: "POST",
    body: category,
  });
}

export async function getDepartments() {
  return normalizeCollection(await request("/departments"));
}

export async function getAssets(filters = {}) {
  return normalizeCollection(await request("/assets", { query: filters }));
}

export async function downloadAssetsExcel(filters = {}) {
  return requestBlob("/assets/export/excel", { query: filters });
}

export async function downloadAssetImportTemplate() {
  return requestBlob("/assets/import/template");
}

export async function previewAssetExcelImport(file) {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormData("/assets/import/preview", formData);
}

export async function commitAssetExcelImport(rows) {
  return request("/assets/import/commit", {
    method: "POST",
    body: { rows },
  });
}

export async function analyzeAssetImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormData("/assets/ocr/analyze", formData, {
    timeoutMs: 30000,
  });
}

export async function getAsset(assetId) {
  return request(`/assets/${assetId}`);
}

export async function getAssetHistory(assetId) {
  return request(`/assets/${assetId}/history`);
}

export async function getActivityLogs({ limit = 100, target_type = "" } = {}) {
  return normalizeCollection(await request("/activity-logs", { query: { limit, target_type } }));
}

export async function getRecentActivityLogs(limit = 10) {
  return normalizeCollection(await request("/activity-logs/recent", { query: { limit } }));
}

export async function getDashboardNotices() {
  return normalizeCollection(await request("/dashboard-notices"));
}

export async function createDashboardNotice(notice) {
  return request("/dashboard-notices", {
    method: "POST",
    body: notice,
    timeoutMs: 8000,
  });
}

export async function updateDashboardNotice(noticeId, notice) {
  return request(`/dashboard-notices/${noticeId}`, {
    method: "PUT",
    body: notice,
    timeoutMs: 8000,
  });
}

export async function deleteDashboardNotice(noticeId, adminPassword) {
  return request(`/dashboard-notices/${noticeId}`, {
    method: "DELETE",
    body: { admin_password: adminPassword },
    timeoutMs: 8000,
  });
}

export async function getWorkManuals() {
  return normalizeCollection(await request("/work-manuals"));
}

export async function getWorkManual(manualId) {
  return request(`/work-manuals/${manualId}`, {
    timeoutMs: 8000,
  });
}

export async function createWorkManual(manual) {
  return request("/work-manuals", {
    method: "POST",
    body: manual,
    timeoutMs: 8000,
  });
}

export async function updateWorkManual(manualId, manual) {
  return request(`/work-manuals/${manualId}`, {
    method: "PUT",
    body: manual,
    timeoutMs: 8000,
  });
}

export async function deleteWorkManual(manualId) {
  return request(`/work-manuals/${manualId}`, {
    method: "DELETE",
    timeoutMs: 8000,
  });
}

export async function uploadWorkManualImage(file) {
  const formData = new FormData();
  formData.append("image", file);
  return requestFormData("/work-manuals/images", formData, {
    timeoutMs: 30000,
  });
}

export async function getVendorContacts(filters = {}) {
  return normalizeCollection(await request("/vendor-contacts", {
    query: filters,
    timeoutMs: 8000,
  }));
}

export async function createVendorContact(contact) {
  return request("/vendor-contacts", {
    method: "POST",
    body: contact,
    timeoutMs: 8000,
  });
}

export async function updateVendorContact(contactId, contact) {
  return request(`/vendor-contacts/${contactId}`, {
    method: "PUT",
    body: contact,
    timeoutMs: 8000,
  });
}

export async function deleteVendorContact(contactId) {
  return request(`/vendor-contacts/${contactId}`, {
    method: "DELETE",
    timeoutMs: 8000,
  });
}

export async function getStatsSummary() {
  return request("/stats/summary");
}

export async function getStatsByCategory() {
  return normalizeCollection(await request("/stats/by-category"));
}

export async function getStatsByDepartment() {
  return normalizeCollection(await request("/stats/by-department"));
}

export async function getStatsMonthly() {
  return normalizeCollection(await request("/stats/monthly"));
}

export async function getSoftwareItems(filters = {}) {
  return normalizeCollection(await request("/software", { query: filters }));
}

export async function getSoftwareStatsSummary() {
  return request("/software/summary");
}

export async function createSoftwareItem(item) {
  return request("/software", {
    method: "POST",
    body: item,
  });
}

export async function updateSoftwareItem(softwareId, item) {
  return request(`/software/${softwareId}`, {
    method: "PUT",
    body: item,
  });
}

export async function deleteSoftwareItem(softwareId) {
  return request(`/software/${softwareId}`, {
    method: "DELETE",
  });
}

export async function getVehicles(filters = {}) {
  return normalizeCollection(await request("/vehicles", { query: filters }));
}

export async function getVehicleSummary() {
  return request("/vehicles/summary");
}

export async function getAdminStatus() {
  return request("/admin/status", {
    timeoutMs: 8000,
  });
}

export async function updateAdminPassword(payload) {
  return request("/admin/password", {
    method: "POST",
    body: payload,
    timeoutMs: 8000,
  });
}

export async function resetAdminPassword(payload) {
  return request("/admin/password/reset", {
    method: "POST",
    body: payload,
    timeoutMs: 8000,
  });
}

export async function verifyAdminPassword(password) {
  return request("/admin/verify", {
    method: "POST",
    body: { password },
    timeoutMs: 8000,
  });
}

export async function createVehicle(vehicle) {
  return request("/vehicles", {
    method: "POST",
    body: vehicle,
  });
}

export async function updateVehicle(vehicleId, vehicle) {
  return request(`/vehicles/${vehicleId}`, {
    method: "PUT",
    body: vehicle,
  });
}

export async function deleteVehicle(vehicleId) {
  return request(`/vehicles/${vehicleId}`, {
    method: "DELETE",
  });
}

export async function getVehicleInsuranceHistories(vehicleId) {
  return normalizeCollection(await request(`/vehicles/${vehicleId}/insurance-histories`));
}

export async function createVehicleInsuranceHistory(vehicleId, history) {
  return request(`/vehicles/${vehicleId}/insurance-histories`, {
    method: "POST",
    body: history,
  });
}

export async function updateVehicleInsuranceHistory(historyId, history) {
  return request(`/vehicles/insurance-histories/${historyId}`, {
    method: "PUT",
    body: history,
  });
}

export async function deleteVehicleInsuranceHistory(historyId) {
  return request(`/vehicles/insurance-histories/${historyId}`, {
    method: "DELETE",
  });
}

export async function getPajuFireInsuranceContracts(filters = {}) {
  return normalizeCollection(await request("/paju-fire-insurance", { query: filters }));
}

export async function getPajuFireInsuranceSummary() {
  return request("/paju-fire-insurance/summary");
}

export async function createPajuFireInsuranceContract(contract) {
  return request("/paju-fire-insurance", {
    method: "POST",
    body: contract,
  });
}

export async function updatePajuFireInsuranceContract(contractId, contract) {
  return request(`/paju-fire-insurance/${contractId}`, {
    method: "PUT",
    body: contract,
  });
}

export async function deletePajuFireInsuranceContract(contractId) {
  return request(`/paju-fire-insurance/${contractId}`, {
    method: "DELETE",
  });
}

export async function getBeverageOrders(filters = {}) {
  return normalizeCollection(await request("/beverage-orders", { query: filters }));
}

export async function getBeverageOrder(orderId) {
  return request(`/beverage-orders/${orderId}`);
}

export async function getBeverageOrderSummary() {
  return request("/beverage-orders/summary");
}

export async function analyzeBeverageOrderAmount(file) {
  const formData = new FormData();
  formData.append("file", file);
  return requestFormData("/beverage-orders/ocr/analyze-amount", formData, {
    timeoutMs: 30000,
  });
}

export async function createBeverageOrder(order) {
  return requestFormData("/beverage-orders", order);
}

export async function updateBeverageOrder(orderId, order) {
  return requestFormData(`/beverage-orders/${orderId}`, order, {
    method: "PUT",
  });
}

export async function deleteBeverageOrder(orderId) {
  return request(`/beverage-orders/${orderId}`, {
    method: "DELETE",
  });
}

export async function createAsset(asset) {
  if (asset?.spec_image_file) {
    return requestFormData("/assets/with-image", buildAssetFormData(asset));
  }
  return request("/assets", {
    method: "POST",
    body: asset,
  });
}

export async function updateAsset(assetId, asset) {
  if (asset?.spec_image_file || asset?.delete_spec_image) {
    return requestFormData(`/assets/${assetId}/with-image`, buildAssetFormData(asset), {
      method: "PUT",
    });
  }
  return request(`/assets/${assetId}`, {
    method: "PUT",
    body: asset,
  });
}

export async function disposeAsset(assetId) {
  return request(`/assets/${assetId}/dispose`, {
    method: "PATCH",
  });
}

export async function deleteAsset(assetId) {
  return request(`/assets/${assetId}`, {
    method: "DELETE",
  });
}

export { API_BASE_URL };

function normalizeCollection(data) {
  if (Array.isArray(data)) {
    return data;
  }
  if (Array.isArray(data?.items)) {
    return data.items;
  }
  if (Array.isArray(data?.logs)) {
    return data.logs;
  }
  if (Array.isArray(data?.results)) {
    return data.results;
  }
  if (Array.isArray(data?.data)) {
    return data.data;
  }
  return [];
}

function getDownloadFilename(contentDisposition) {
  if (!contentDisposition) {
    return "";
  }

  const utfFilename = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfFilename?.[1]) {
    return decodeURIComponent(utfFilename[1]);
  }

  const asciiFilename = contentDisposition.match(/filename="?([^";]+)"?/i);
  return asciiFilename?.[1] || "";
}

function buildAssetFormData(asset) {
  const formData = new FormData();
  Object.entries(asset || {}).forEach(([key, value]) => {
    if (key === "spec_image_file") {
      if (value) {
        formData.append("spec_image", value);
      }
      return;
    }
    if (key === "delete_spec_image") {
      if (value) {
        formData.append("delete_spec_image", "true");
      }
      return;
    }
    if (value !== undefined && value !== null) {
      formData.append(key, String(value));
    }
  });
  return formData;
}

function buildInstallFileFormData(payload) {
  const formData = new FormData();
  Object.entries(payload || {}).forEach(([key, value]) => {
    if (key === "file") {
      if (value) {
        formData.append("file", value);
      }
      return;
    }
    if (value !== undefined && value !== null) {
      formData.append(key, typeof value === "boolean" ? String(value) : String(value));
    }
  });
  return formData;
}

function getAdminAuthHeaders() {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    const storedValue = window.sessionStorage.getItem("assetManager.adminAuth");
    if (!storedValue) {
      return {};
    }
    const parsedValue = JSON.parse(storedValue);
    const expiresAt = Date.parse(parsedValue?.expires_at || "");
    if (!parsedValue?.token || !String(parsedValue.token).includes(".") || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      window.sessionStorage.removeItem("assetManager.adminAuth");
      return {};
    }
    return { "X-Admin-Auth": parsedValue.token };
  } catch {
    window.sessionStorage.removeItem("assetManager.adminAuth");
    return {};
  }
}

function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function handleUnauthorized(response) {
  if (response.status !== 401 || typeof window === "undefined") {
    return;
  }
  clearAuthToken();
  window.dispatchEvent(new CustomEvent("asset-manager-auth-expired"));
}
