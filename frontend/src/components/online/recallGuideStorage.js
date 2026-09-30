export const RECALL_GUIDE_STORAGE_KEY = "recallGuideVersion";
export const RECALL_GUIDE_VERSION = "v1";

export function shouldShowRecallGuide() {
  try { return window.localStorage.getItem(RECALL_GUIDE_STORAGE_KEY) !== RECALL_GUIDE_VERSION; }
  catch { return true; }
}

export function saveRecallGuideDismissal() {
  try { window.localStorage.setItem(RECALL_GUIDE_STORAGE_KEY, RECALL_GUIDE_VERSION); }
  catch { /* The guide still closes when browser storage is unavailable. */ }
}
