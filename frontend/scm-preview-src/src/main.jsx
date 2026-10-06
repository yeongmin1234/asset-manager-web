import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./employee-lifecycle.css";
import "./scm-site.css";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./contexts/AuthContext";
import LoginPage from "./LoginPage";

function AuthenticatedApplication() {
  const { ready, isAuthenticated } = useAuth();
  if (!ready) return <main className="scm-auth-loading" role="status">로그인 상태를 확인하고 있습니다.</main>;
  return isAuthenticated ? <App /> : <LoginPage />;
}

function hasScmSiteParent() {
  try {
    return window.parent !== window
      && window.parent.location.origin === window.location.origin
      && (window.parent.location.pathname === "/scm-app" || window.parent.location.pathname.startsWith("/scm-app/"));
  } catch {
    return false;
  }
}

if (!hasScmSiteParent()) {
  // The standalone static document has no site JWT guard; use the authenticated parent route.
  window.location.replace("/scm-app");
} else {
  document.body.classList.add("scm-embedded");
  ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
      <AuthProvider>
        <AuthenticatedApplication />
      </AuthProvider>
    </React.StrictMode>,
  );
}
