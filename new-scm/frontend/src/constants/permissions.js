import { ACCOUNT_TYPES } from "./accountTypes";
export const ACCOUNT_STATUS = {
  ACTIVE: "active",
  SUSPENDED: "suspended",
};

const actionNames = { create: "data.create", read: "data.read", update: "data.update", delete: "data.delete" };

export const canAccessPath = (user, path) => {
  if (user?.status !== ACCOUNT_STATUS.ACTIVE || !user.action_grants?.includes("system.access")) return false;
  if (typeof path !== "string" || !user.menu_grants?.includes(path)) return false;
  return !path.startsWith("/settings") || (
    user.account_type === ACCOUNT_TYPES.ADMIN && user.action_grants.includes("admin.manage")
  );
};

export const canPerform = (user, action) => Boolean(user?.status === ACCOUNT_STATUS.ACTIVE
  && user.action_grants?.includes("system.access")
  && typeof action === "string"
  && user.action_grants.includes(actionNames[action] || action));
