// Marketplace controls remain local to the copied preview.
const unavailable = async () => { throw new Error("마켓 API는 아직 연결되지 않았습니다."); };
export const marketplaceApiConfigured = false;
export const getMarketplaces = unavailable;
export const getActiveMarketplaces = unavailable;
export const createMarketplace = unavailable;
export const activateMarketplace = unavailable;
export const deactivateMarketplace = unavailable;
export const getMarketplaceSalesUsage = unavailable;
