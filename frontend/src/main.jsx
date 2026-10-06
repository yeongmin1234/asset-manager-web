import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { clearAuthToken, getAuthToken, getCurrentUser, login, logout } from "./api/client.js";
import LoginPage from "./components/LoginPage.jsx";


function AuthenticatedApp() {
  const [state, setState] = useState(() => ({
    error: "",
    loading: Boolean(getAuthToken()),
    submitting: false,
    user: null,
  }));

  useEffect(() => {
    const expire = () => {
      window.history.replaceState({}, "", "/login");
      setState({ error: "로그인이 만료되었습니다.", loading: false, submitting: false, user: null });
    };
    window.addEventListener("asset-manager-auth-expired", expire);
    if (!getAuthToken()) {
      setState((current) => ({ ...current, loading: false }));
    } else {
      getCurrentUser()
        .then((user) => {
          if (window.location.pathname === "/login" || window.location.pathname === "/") {
            window.history.replaceState({}, "", "/select-system");
          }
          setState({ error: "", loading: false, submitting: false, user });
        })
        .catch(() => {
          clearAuthToken();
          window.history.replaceState({}, "", "/login");
          setState({ error: "다시 로그인해 주세요.", loading: false, submitting: false, user: null });
        });
    }
    return () => window.removeEventListener("asset-manager-auth-expired", expire);
  }, []);

  useEffect(() => {
    if (state.loading || state.user) return undefined;
    const keepLoginPath = () => {
      if (window.location.pathname !== "/login") window.history.replaceState({}, "", "/login");
    };
    keepLoginPath();
    window.addEventListener("popstate", keepLoginPath);
    return () => window.removeEventListener("popstate", keepLoginPath);
  }, [state.loading, state.user]);

  const handleLogin = async ({ username, password }) => {
    setState((current) => ({ ...current, error: "", submitting: true }));
    try {
      const result = await login(username, password);
      window.history.pushState({}, "", "/select-system");
      setState({ error: "", loading: false, submitting: false, user: result.user });
    } catch (error) {
      setState({ error: error.message, loading: false, submitting: false, user: null });
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error("[AssetManager] logout access log request failed", error);
    } finally {
      clearAuthToken();
      window.history.replaceState({}, "", "/login");
      setState({ error: "", loading: false, submitting: false, user: null });
    }
  };

  if (state.loading) {
    return <main className="login-page"><div className="login-loading">로그인 확인 중...</div></main>;
  }
  if (!state.user) {
    return <LoginPage error={state.error} isSubmitting={state.submitting} onSubmit={handleLogin} />;
  }
  return <App currentUser={state.user} onLogout={handleLogout} />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthenticatedApp />
  </React.StrictMode>,
);
