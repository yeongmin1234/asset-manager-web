import React from "react";
import { useAuth } from "../../contexts/AuthContext";
import { ACCOUNT_TYPES } from "../../constants/accountTypes";

export default function AdminOnly({ children, fallback = null }) {
  const { currentUser } = useAuth();
  return currentUser.status === "active" && currentUser.accountType === ACCOUNT_TYPES.ADMIN ? children : fallback;
}
