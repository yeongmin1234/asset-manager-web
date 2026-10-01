import React, { Suspense, useState } from "react";
import LoginClock from "./LoginClock.jsx";

const SAVED_USERNAME_KEY = "asset_manager_saved_username";
const CUP_RIM = { x: 0.142, y: 0.774 };
const AutumnAtmosphere = React.lazy(() => import("./AutumnAtmosphere.jsx"));


function LoginPage({ error = "", isSubmitting = false, onSubmit }) {
  const [initialSavedUsername] = useState(readSavedUsername);
  const [username, setUsername] = useState(initialSavedUsername);
  const [password, setPassword] = useState("");
  const [rememberUsername, setRememberUsername] = useState(Boolean(initialSavedUsername));

  const handleSubmit = (event) => {
    event.preventDefault();
    const normalizedUsername = username.trim();
    updateSavedUsername(rememberUsername ? normalizedUsername : "");
    onSubmit?.({ username: normalizedUsername, password });
  };

  const handleRememberUsername = (event) => {
    const checked = event.target.checked;
    setRememberUsername(checked);
    if (!checked) {
      updateSavedUsername("");
    }
  };

  return (
    <main className="login-page">
      <Suspense fallback={null}><AutumnAtmosphere cupPosition={CUP_RIM} /></Suspense>
      <div className="login-company">
        <strong>The Limo &amp;</strong>
        <span className="login-company-divider" aria-hidden="true" />
        <span>자산관리 시스템</span>
      </div>
      <section className="login-panel">
        <div className="login-form-wrap">
          <LoginClock />
          <div className="login-form-card">
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="login-heading">
                <span className="login-eyebrow">A QUIET MOMENT</span>
                <h1>반가워요.</h1>
                <p>오늘의 일상을 시작해 보세요.</p>
              </div>

              <div className="login-fields">
                <label>
                  <span>아이디</span>
                  <input autoComplete="username" autoFocus placeholder="아이디를 입력하세요" value={username} onChange={(event) => setUsername(event.target.value)} required />
                </label>
                <label>
                  <span>비밀번호</span>
                  <input autoComplete="current-password" placeholder="비밀번호를 입력하세요" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
                </label>
                <label className="login-remember">
                  <input
                    type="checkbox"
                    checked={rememberUsername}
                    onChange={handleRememberUsername}
                  />
                  <span>아이디 저장</span>
                </label>
                {error ? <p className="login-error" role="alert">{error}</p> : null}
                <button className="login-submit" disabled={isSubmitting} type="submit">
                  <span>{isSubmitting ? "로그인 중..." : "로그인"}</span>
                  <span aria-hidden="true">→</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

    </main>
  );
}

function readSavedUsername() {
  try {
    return window.localStorage.getItem(SAVED_USERNAME_KEY) || "";
  } catch {
    return "";
  }
}

function updateSavedUsername(username) {
  try {
    if (username) {
      window.localStorage.setItem(SAVED_USERNAME_KEY, username);
    } else {
      window.localStorage.removeItem(SAVED_USERNAME_KEY);
    }
  } catch {
    // Login remains available when browser storage is blocked.
  }
}

export default LoginPage;
