// The existing settings endpoints are not part of the independent stage 3 API.
const unavailable = async () => { throw new Error("설정 API는 다음 단계에서 연결합니다."); };
export const settingsApiConfigured = false;
export const settingsApi = Object.freeze({
  groups: unavailable,
  settings: unavailable,
  symptoms: unavailable,
  parts: unavailable,
  templates: unavailable,
  optOuts: unavailable,
  smsLogs: unavailable,
  batches: unavailable,
  runBatch: unavailable,
  serialJobs: unavailable,
  serialAction: unavailable,
  uploadSerial: unavailable,
});
