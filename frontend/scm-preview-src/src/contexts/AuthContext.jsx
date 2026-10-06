import React, { createContext, useCallback, useContext, useMemo } from "react";
import { canAccessPath, canPerform } from "../constants/permissions";
import { CURRENT_USER_MOCK } from "../mocks/currentUserMock";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Preview-only identity: no token is read and no production login is called.
  const currentUser = CURRENT_USER_MOCK;
  const ready = true;
  const login = useCallback(async () => { throw new Error("미리보기에서는 로그인을 사용할 수 없습니다."); }, []);
  const logout = useCallback(() => {}, []);

  const value = useMemo(() => ({
    currentUser,
    ready,
    isAuthenticated: Boolean(currentUser),
    isLoading: !ready,
    isDevMode: true,
    login,
    logout,
    canAccess: (path) => Boolean(currentUser) && canAccessPath(currentUser, path),
    can: () => Boolean(currentUser) && canPerform(currentUser.status),
  }), [currentUser, ready, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider가 필요합니다.");
  return value;
};
