const pending = new Map();

if (typeof window !== "undefined") {
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.source !== window.parent) return;
    if (event.data?.type !== "scm-activity:response") return;
    const entry = pending.get(event.data.requestId);
    if (!entry) return;
    pending.delete(event.data.requestId);
    window.clearTimeout(entry.timer);
    if (event.data.error) entry.reject(new Error(event.data.error));
    else entry.resolve(event.data.data);
  });
}

function request(operation, payload) {
  if (window.parent === window) return Promise.reject(new Error("SCM 화면에서만 작업 기록을 볼 수 있습니다."));
  const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      pending.delete(requestId);
      reject(new Error("작업 기록 요청 시간이 초과되었습니다."));
    }, 10000);
    pending.set(requestId, { resolve, reject, timer });
    window.parent.postMessage({ type: "scm-activity:request", requestId, operation, payload }, window.location.origin);
  });
}

export const getRecentActivity = () => request("dashboard");
export const getActivityHistory = (filters) => request("list", filters);
export const recordActivity = (module, action) => request("record", { module, action });

export function recordPreviewActivity(module, action) {
  recordActivity(module, action).catch(() => {
    // The preview action remains local even if audit storage is unavailable.
  });
}
