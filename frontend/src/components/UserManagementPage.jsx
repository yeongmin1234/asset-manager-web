import React, { useEffect, useState } from "react";
import {
  createUser,
  deactivateUser,
  getUsers,
  resetUserPassword,
  updateUser,
} from "../api/client.js";


const EMPTY_CREATE_FORM = { username: "", name: "", password: "", role: "user" };


function UserManagementPage() {
  const [users, setUsers] = useState([]);
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [drafts, setDrafts] = useState({});
  const [resetPasswords, setResetPasswords] = useState({});
  const [state, setState] = useState({ error: "", loading: true, message: "", savingId: null });

  const loadUsers = async () => {
    setState((current) => ({ ...current, error: "", loading: true }));
    try {
      const items = await getUsers();
      setUsers(items);
      setDrafts(Object.fromEntries(items.map((user) => [
        user.id,
        { name: user.name, role: user.role, is_active: user.is_active },
      ])));
      setState((current) => ({ ...current, loading: false }));
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, loading: false }));
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const runAction = async (action, successMessage, savingId = "create") => {
    setState((current) => ({ ...current, error: "", message: "", savingId }));
    try {
      await action();
      await loadUsers();
      setState((current) => ({ ...current, loading: false, message: successMessage, savingId: null }));
      return true;
    } catch (error) {
      setState((current) => ({ ...current, error: error.message, savingId: null }));
      return false;
    }
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    const success = await runAction(
      () => createUser(createForm),
      "사용자를 생성했습니다.",
    );
    setCreateForm((current) => ({ ...current, password: "" }));
    if (success) {
      setCreateForm(EMPTY_CREATE_FORM);
    }
  };

  const handleUpdate = (userId) =>
    runAction(() => updateUser(userId, drafts[userId]), "사용자 정보를 수정했습니다.", userId);

  const handleResetPassword = async (userId) => {
    const password = resetPasswords[userId] || "";
    await runAction(
      () => resetUserPassword(userId, password),
      "비밀번호를 초기화했습니다.",
      userId,
    );
    setResetPasswords((current) => ({ ...current, [userId]: "" }));
  };

  const handleDeactivate = (userId) =>
    runAction(() => deactivateUser(userId), "사용자를 비활성화했습니다.", userId);

  const updateDraft = (userId, field, value) => {
    setDrafts((current) => ({
      ...current,
      [userId]: { ...current[userId], [field]: value },
    }));
  };

  return (
    <section className="user-management-page">
      <div className="portal-screen-heading">
        <h2>사용자 관리</h2>
        <p>계정을 생성하고 권한, 활성 상태와 비밀번호를 관리합니다.</p>
      </div>

      <form className="user-create-panel" onSubmit={handleCreate}>
        <input placeholder="ID" value={createForm.username} onChange={(event) => setCreateForm({ ...createForm, username: event.target.value })} required />
        <input placeholder="이름" value={createForm.name} onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })} required />
        <input placeholder="비밀번호 (8자 이상)" type="password" minLength={8} autoComplete="new-password" value={createForm.password} onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })} required />
        <select value={createForm.role} onChange={(event) => setCreateForm({ ...createForm, role: event.target.value })}>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <button type="submit" disabled={state.savingId !== null}>사용자 생성</button>
      </form>

      {state.message ? <p className="user-management-message">{state.message}</p> : null}
      {state.error ? <p className="user-management-error">{state.error}</p> : null}

      <div className="user-table-wrap">
        <table className="user-table">
          <thead>
            <tr><th>ID</th><th>이름</th><th>권한</th><th>상태</th><th>생성일</th><th>수정일</th><th>관리</th></tr>
          </thead>
          <tbody>
            {state.loading ? <tr><td colSpan="7">불러오는 중...</td></tr> : users.map((user) => {
              const draft = drafts[user.id] || user;
              return (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td><input value={draft.name} onChange={(event) => updateDraft(user.id, "name", event.target.value)} /></td>
                  <td><select value={draft.role} onChange={(event) => updateDraft(user.id, "role", event.target.value)}><option value="user">user</option><option value="admin">admin</option></select></td>
                  <td><label><input type="checkbox" checked={draft.is_active} onChange={(event) => updateDraft(user.id, "is_active", event.target.checked)} /> {draft.is_active ? "활성" : "비활성"}</label></td>
                  <td>{formatDate(user.created_at)}</td>
                  <td>{formatDate(user.updated_at)}</td>
                  <td className="user-actions">
                    <button type="button" onClick={() => handleUpdate(user.id)} disabled={state.savingId !== null}>저장</button>
                    <input type="password" minLength={8} autoComplete="new-password" placeholder="새 비밀번호" value={resetPasswords[user.id] || ""} onChange={(event) => setResetPasswords({ ...resetPasswords, [user.id]: event.target.value })} />
                    <button type="button" onClick={() => handleResetPassword(user.id)} disabled={state.savingId !== null || (resetPasswords[user.id] || "").length < 8}>초기화</button>
                    <button type="button" className="danger-button" onClick={() => handleDeactivate(user.id)} disabled={state.savingId !== null || !user.is_active}>비활성화</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ko-KR");
}

export default UserManagementPage;
