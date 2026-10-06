import{useAuth}from"../contexts/AuthContext";
export const usePermission=action=>useAuth().can(action);
