import React, { useState } from "react";

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
      <section className="login-card">
        <div className="login-brand">
          <img src="/logo.png" alt="Asset Manager" />
          <h1>자산관리 시스템</h1>
          <p>계속하려면 계정으로 로그인하세요.</p>
        </div>
        <form onSubmit={handleSubmit}>
          <label>ID
            <input autoComplete="username" autoFocus value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          <label>비밀번호
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
          {error ? <p className="login-error">{error}</p> : null}
          <button disabled={isSubmitting} type="submit">{isSubmitting ? "로그인 중..." : "로그인"}</button>
        </form>
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
