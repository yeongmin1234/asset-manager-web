// Stage 3 intentionally has no AI or external inventory API.
const unavailable = async () => { throw new Error("신규 SCM 업무 API는 아직 연결되지 않았습니다."); };
export const homeAssistantApiConfigured = false;
export const chatAssistant = unavailable;
export const searchECountItems = unavailable;
export const getECountInventory = unavailable;
export const getVipCustomerStatus = unavailable;
