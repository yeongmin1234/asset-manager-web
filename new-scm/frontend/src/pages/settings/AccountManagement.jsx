import React, { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { authRequest } from "../../services/authService";

export default function AccountManagement() {
  const { currentUser, can } = useAuth();
  const [users, setUsers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [password, setPassword] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const allowed = currentUser?.account_type === "admin" && can("admin.manage");
  const load = () => authRequest("/admin/auth/users").then(data => setUsers(data.users));
  useEffect(() => { if (allowed) load().catch(() => setMessage("계정 목록을 확인할 수 없습니다.")); }, [allowed]);
  if (!allowed) return <p role="alert">관리자 권한이 필요합니다.</p>;
  async function save(event) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      await authRequest(`/admin/auth/users/${selected.id}/credentials`, { method: "POST",
        body: JSON.stringify({ password: password || null, enabled }) });
      setSelected(null); setMessage("저장했습니다. 해당 사용자의 기존 세션은 만료되었습니다."); await load();
    } catch { setMessage("저장하지 못했습니다. 권한과 비밀번호 길이(12–256자)를 확인해주세요."); }
    finally { setPassword(""); setBusy(false); }
  }
  return <section className="settings-panel"><h2>SCM 로그인 계정 관리</h2>
    <p>기존 SCM 사용자에 전용 비밀번호를 설정하거나 로그인을 차단합니다. 사용자 및 업무 권한 추가는 승인된 관리자 절차로 진행하세요.</p>
    {message && <p role="status">{message}</p>}
    <table><thead><tr><th>아이디</th><th>이름</th><th>권한</th><th>로그인</th><th>관리</th></tr></thead>
      <tbody>{users.map(user => <tr key={user.id}><td>{user.username}</td><td>{user.name}</td>
        <td>{user.account_type}</td><td>{user.status === "active" && user.login_enabled ? "허용" : "차단 / 미설정"}</td>
        <td><button disabled={busy || String(user.id) === currentUser.subject || user.status !== "active"}
          onClick={() => { setSelected(user); setEnabled(user.login_enabled); setPassword(""); }}>로그인 설정</button></td></tr>)}</tbody></table>
    {selected && <form onSubmit={save}><h3>{selected.username} 로그인 설정</h3>
      <label>새 비밀번호<input type="password" autoComplete="new-password" minLength={12} maxLength={256}
        required={!selected.credentials_configured} value={password} onChange={e => setPassword(e.target.value)} disabled={busy}/></label>
      <label><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} disabled={busy}/>로그인 허용</label>
      <button disabled={busy}>저장 및 세션 만료</button><button type="button" disabled={busy}
        onClick={() => { setSelected(null); setPassword(""); }}>취소</button></form>}
  </section>;
}
