const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";
const REQUEST_TIMEOUT_MS = 6000;

export class ApiError extends Error {
  constructor(message, { status, detail } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

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
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  };

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (error) {
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
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
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
    });
  }

  return data;
}

async function requestBlob(path, options = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

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
        ...options.headers,
      },
    });
  } catch (error) {
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    let data = null;
    try {
      data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
    } catch {
      data = null;
    }
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
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
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(url, {
      method: options.method || "POST",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...options.headers,
      },
      body: formData,
    });
  } catch (error) {
    const message =
      error.name === "AbortError"
        ? "Backend 응답 시간이 초과되었습니다."
        : "Backend에 연결할 수 없습니다.";
    throw new ApiError(message, {
      detail: error.message,
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
    throw new ApiError(getErrorMessage(data, response.status), {
      status: response.status,
      detail: data,
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

export async function getHealth() {
  return request("/health");
}

export async function getDatabaseHealth() {
  return request("/health/db");
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

export async function getAsset(assetId) {
  return request(`/assets/${assetId}`);
}

export async function getAssetHistory(assetId) {
  return request(`/assets/${assetId}/history`);
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

export async function createAsset(asset) {
  return request("/assets", {
    method: "POST",
    body: asset,
  });
}

export async function updateAsset(assetId, asset) {
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
