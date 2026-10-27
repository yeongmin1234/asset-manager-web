// 권한 등급은 사용하지 않습니다. 활성 계정은 모든 표시 메뉴와 업무 기능을 사용합니다.
import { ACCOUNT_TYPES } from "./accountTypes";
export const ACCOUNT_STATUS = {
  ACTIVE: "active",
  SUSPENDED: "suspended",
};

export const canAccessPath = (user, path) => user.status === ACCOUNT_STATUS.ACTIVE
  && (!path.startsWith("/settings") || user.accountType === ACCOUNT_TYPES.ADMIN);
export const canPerform = (status) => status === ACCOUNT_STATUS.ACTIVE;
