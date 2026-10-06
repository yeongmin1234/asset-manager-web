export const ACCOUNT_TYPES = {
  ADMIN: "admin",
  EMPLOYEE: "employee",
};

export const ACCOUNT_TYPE_OPTIONS = [
  { value: ACCOUNT_TYPES.EMPLOYEE, label: "일반 임직원" },
  { value: ACCOUNT_TYPES.ADMIN, label: "관리자" },
];

export const getAccountTypeLabel = (type) => ACCOUNT_TYPE_OPTIONS.find((option) => option.value === type)?.label ?? type;
