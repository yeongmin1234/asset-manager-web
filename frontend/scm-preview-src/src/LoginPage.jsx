import React, { useState } from "react";
import SkoomiMascot from "./components/common/SkoomiMascot";
import { useAuth } from "./contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (!username.trim() || !password || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await login(username, password, remember);
    } catch (reason) {
      setError(reason.message || "로그인에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="scm-login">
      <section className="scm-login__card" aria-labelledby="scm-login-title">
        <div className="scm-login__form">
          <p className="scm-login__eyebrow">NEW SCM</p>
          <h1 id="scm-login-title">신규 SCM 로그인</h1>
          <p>업무 계정으로 로그인해주세요.</p>
          <form onSubmit={submit}>
            <label><span>아이디</span><input autoFocus autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
            <label><span>비밀번호</span><input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <label className="scm-login__remember"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />로그인 유지</label>
            {error && <p className="scm-login__error" role="alert">{error}</p>}
            <button type="submit" className="primary" disabled={submitting || !username.trim() || !password}>{submitting ? "로그인 중..." : "로그인"}</button>
          </form>
        </div>
        <SkoomiMascot state={error ? "error" : "default"} size="large" message={error ? "로그인 정보를 다시 확인해주세요." : "신규 SCM에 오신 것을 환영합니다. 스쿠미가 업무를 도와드릴게요."} />
      </section>
    </main>
  );
}
