import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { canAccessPath, canPerform } from "../constants/permissions";
import { restoreSession, login as signIn, logout as signOut } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const generation = useRef(0);

  useEffect(() => {
    let active = true;
    restoreSession().then(
      (user) => { if (active) setCurrentUser(user); },
      () => { if (active) setCurrentUser(null); },
    ).finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const expired = () => { generation.current += 1; setCurrentUser(null); };
    const refresh = () => {
      const expected = generation.current;
      restoreSession().then(user => { if (expected === generation.current) setCurrentUser(user); })
        .catch(() => { if (expected === generation.current) setCurrentUser(null); });
    };
    const timer = window.setInterval(refresh, 60000);
    window.addEventListener("scm-session-expired", expired);
    window.addEventListener("focus", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh);
      window.removeEventListener("scm-session-expired", expired); };
  }, []);

  const value = useMemo(() => ({
    currentUser,
    ready: !isLoading,
    isAuthenticated: Boolean(currentUser),
    isLoading,
    isDevMode: false,
    login: async (username, password) => {
      generation.current += 1;
      await signIn(username, password);
      const user = await restoreSession();
      if (!user) throw Object.assign(new Error("session_unavailable"), { status: 401 });
      generation.current += 1;
      setCurrentUser(user);
    },
    logout: async () => { generation.current += 1; await signOut(); generation.current += 1; setCurrentUser(null); },
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
