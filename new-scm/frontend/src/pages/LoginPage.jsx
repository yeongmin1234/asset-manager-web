import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import "./login.css";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try { await login(username, password); }
    catch (failure) {
      setError(failure.status === 429 ? "로그인 시도가 많습니다. 15분 후 다시 시도해주세요."
        : failure.status === 503 ? "인증 서비스를 확인해주세요. 관리자에게 문의하세요."
        : "아이디 또는 비밀번호를 확인해주세요.");
    } finally { setPassword(""); setBusy(false); }
  }
  return <main className="scm-login"><form onSubmit={submit} className="scm-login__card">
    <p>SCM WORKSPACE</p><h1>SCM 로그인</h1>
    <label>아이디<input autoComplete="username" name="username" required maxLength={50}
      value={username} onChange={e => setUsername(e.target.value)} disabled={busy}/></label>
    <label>비밀번호<input type="password" autoComplete="current-password" name="password"
      required maxLength={256} value={password} onChange={e => setPassword(e.target.value)} disabled={busy}/></label>
    {error && <p role="alert">{error}</p>}
    <button type="submit" disabled={busy}>{busy ? "로그인 중…" : "로그인"}</button>
    <small>SCM 전용 계정을 사용하세요. 최초 비밀번호는 관리자에게 설정을 요청하세요.</small>
  </form></main>;
}
