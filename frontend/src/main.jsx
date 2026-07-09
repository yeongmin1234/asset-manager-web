import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { clearAuthToken, getAuthToken, getCurrentUser, login } from "./api/client.js";
import LoginPage from "./components/LoginPage.jsx";


function AuthenticatedApp() {
  const [state, setState] = useState(() => ({
    error: "",
    loading: Boolean(getAuthToken()),
    submitting: false,
    user: null,
  }));

  useEffect(() => {
    const expire = () => setState({ error: "로그인이 만료되었습니다.", loading: false, submitting: false, user: null });
    window.addEventListener("asset-manager-auth-expired", expire);
    if (!getAuthToken()) {
      setState((current) => ({ ...current, loading: false }));
    } else {
      getCurrentUser()
        .then((user) => setState({ error: "", loading: false, submitting: false, user }))
        .catch(() => {
          clearAuthToken();
          setState({ error: "다시 로그인해 주세요.", loading: false, submitting: false, user: null });
        });
    }
    return () => window.removeEventListener("asset-manager-auth-expired", expire);
  }, []);

  const handleLogin = async ({ username, password }) => {
    setState((current) => ({ ...current, error: "", submitting: true }));
    try {
      const result = await login(username, password);
      setState({ error: "", loading: false, submitting: false, user: result.user });
    } catch (error) {
      setState({ error: error.message, loading: false, submitting: false, user: null });
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    setState({ error: "", loading: false, submitting: false, user: null });
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
