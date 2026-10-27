// Stage 3 preview is independent. No parent bridge or legacy backend request.
export const getRecentActivity = async () => ({ recent_activity: [] });
export const getActivityHistory = async () => ({ items: [], total: 0 });
export const recordActivity = async () => null;
export function recordPreviewActivity() {}
