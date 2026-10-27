import React from "react";
import { useAuth } from "../../contexts/AuthContext";
import { ACCOUNT_TYPES } from "../../constants/accountTypes";

export default function AdminOnly({ children, fallback = null }) {
  const { currentUser } = useAuth();
  return currentUser?.status === "active"
    && currentUser.account_type === ACCOUNT_TYPES.ADMIN
    && currentUser.action_grants?.includes("system.access")
    && currentUser.action_grants.includes("admin.manage") ? children : fallback;
}
