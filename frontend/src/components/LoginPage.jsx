import React, { useState } from "react";


function LoginPage({ error = "", isSubmitting = false, onSubmit }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.({ username: username.trim(), password });
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <img src="/logo.png" alt="Asset Manager" />
        <h1>자산관리 시스템</h1>
        <p>계속하려면 계정으로 로그인하세요.</p>
        <form onSubmit={handleSubmit}>
          <label>아이디
            <input autoComplete="username" autoFocus value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          <label>비밀번호
            <input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          {error ? <p className="login-error">{error}</p> : null}
          <button disabled={isSubmitting} type="submit">{isSubmitting ? "로그인 중..." : "로그인"}</button>
        </form>
      </section>
    </main>
  );
}

export default LoginPage;
