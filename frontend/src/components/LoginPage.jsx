import React, { useState } from "react";
import AiButton from "./animata/button/AiButton.jsx";
import LoginVisual from "./LoginVisual.jsx";

const SAVED_USERNAME_KEY = "asset_manager_saved_username";


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
      <section className="login-panel">
        <div className="login-company">
          <img src="/logo.png" alt="" />
          <span>자산관리 시스템</span>
        </div>

        <div className="login-form-wrap">
          <div className="login-form-card">
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="login-heading">
                <h1>로그인</h1>
                <p>계정 정보를 입력하여 시스템에 로그인하세요.</p>
              </div>

              <div className="login-fields">
                <label>
                  <span>아이디</span>
                  <input autoComplete="username" autoFocus value={username} onChange={(event) => setUsername(event.target.value)} required />
                </label>
                <label>
                  <span>비밀번호</span>
                  <input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
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
                <AiButton disabled={isSubmitting} loading={isSubmitting} type="submit">로그인</AiButton>
              </div>
            </form>
          </div>
        </div>
      </section>

      <LoginVisual />
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
