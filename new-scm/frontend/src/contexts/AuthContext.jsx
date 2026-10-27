import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { canAccessPath, canPerform } from "../constants/permissions";
import { restoreSession } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    restoreSession().then(
      (user) => { if (active) setCurrentUser(user); },
      () => { if (active) setCurrentUser(null); },
    ).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, []);

  const value = useMemo(() => ({
    currentUser,
    ready: !isLoading,
    isAuthenticated: Boolean(currentUser),
    isLoading,
    isDevMode: false,
    canAccess: (path) => Boolean(currentUser) && canAccessPath(currentUser, path),
    can: (action) => Boolean(currentUser) && canPerform(currentUser, action),
  }), [currentUser, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider가 필요합니다.");
  return value;
};
