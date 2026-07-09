import React, { useEffect, useState } from "react";
import {
  createUser,
  deactivateUser,
  getUsers,
  resetUserPassword,
  updateUser,
} from "../api/client.js";


const MENU_OPTIONS = [
  ["dashboard", "대시보드"],
  ["beverage-orders", "음료주문기록"],
  ["work-manuals", "업무설명서"],
  ["vendor-contacts", "업체연락처"],
  ["assets", "자산 관리"],
  ["software", "SW 현황"],
  ["vehicles", "법인차량 관리"],
  ["paju-fire-insurance", "파주화재보험"],
  ["network", "네트워크 현황"],
  ["stats", "통계 / 리포트"],
  ["history", "변경 이력"],
];
const EMPTY_CREATE_FORM = {
  username: "",
  name: "",
  password: "",
  role: "user",
  menu_permissions: ["dashboard", "assets"],
};


function UserManagementPage() {
  const [users, setUsers] = useState([]);
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [drafts, setDrafts] = useState({});
  const [resetPasswords, setResetPasswords] = useState({});
  const [permissionUserId, setPermissionUserId] = useState(null);
  const [state, setState] = useState({ error: "", loading: true, message: "", savingId: null });

  const loadUsers = async () => {
    setState((current) => ({ ...current, error: "", loading: true }));
    try {
      const items = await getUsers();
      setUsers(items);
      setDrafts(Object.fromEntries(items.map((user) => [
        user.id,
        {
          name: user.name,
          role: user.role,
          is_active: user.is_active,
          menu_permissions: user.menu_permissions || [],
        },
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

  const handleDeactivate = (user) => {
    const confirmed = window.confirm(
      `${user.username} 계정을 삭제(비활성화)하시겠습니까?`,
    );
    if (!confirmed) return;
    runAction(
      () => deactivateUser(user.id),
      "사용자를 삭제(비활성화)했습니다.",
      user.id,
    );
  };

  const updateDraft = (userId, field, value) => {
    setDrafts((current) => ({
      ...current,
      [userId]: { ...current[userId], [field]: value },
    }));
  };

  const togglePermission = (userId, permission) => {
    const selected = drafts[userId]?.menu_permissions || [];
    updateDraft(
      userId,
      "menu_permissions",
      selected.includes(permission)
        ? selected.filter((item) => item !== permission)
        : [...selected, permission],
    );
  };

  const toggleCreatePermission = (permission) => {
    const selected = createForm.menu_permissions;
    setCreateForm({
      ...createForm,
      menu_permissions: selected.includes(permission)
        ? selected.filter((item) => item !== permission)
        : [...selected, permission],
    });
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
        <details className="user-create-permissions">
          <summary>기본 메뉴 권한</summary>
          <div className="user-permission-grid">
            {MENU_OPTIONS.map(([id, label]) => (
              <label key={id}>
                <input
                  type="checkbox"
                  checked={createForm.role === "admin" || createForm.menu_permissions.includes(id)}
                  disabled={createForm.role === "admin"}
                  onChange={() => toggleCreatePermission(id)}
                />
                {label}
              </label>
            ))}
          </div>
        </details>
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
                  <td>
                    <select value={draft.role} onChange={(event) => updateDraft(user.id, "role", event.target.value)}><option value="user">user</option><option value="admin">admin</option></select>
                    {draft.role === "admin" ? <span className="all-access-badge">전체 권한</span> : null}
                  </td>
                  <td><label className="user-status-toggle"><input type="checkbox" checked={draft.is_active} onChange={(event) => updateDraft(user.id, "is_active", event.target.checked)} /> {draft.is_active ? "활성" : "비활성"}</label></td>
                  <td>{formatDate(user.created_at)}</td>
                  <td>{formatDate(user.updated_at)}</td>
                  <td className="user-actions">
                    <button type="button" onClick={() => handleUpdate(user.id)} disabled={state.savingId !== null}>저장</button>
                    <button type="button" className="outline-button" onClick={() => setPermissionUserId(user.id)}>메뉴 권한</button>
                    <input type="password" minLength={8} autoComplete="new-password" placeholder="새 비밀번호" value={resetPasswords[user.id] || ""} onChange={(event) => setResetPasswords({ ...resetPasswords, [user.id]: event.target.value })} />
                    <button type="button" onClick={() => handleResetPassword(user.id)} disabled={state.savingId !== null || (resetPasswords[user.id] || "").length < 8}>초기화</button>
                    <button type="button" className="danger-button" onClick={() => handleDeactivate(user)} disabled={state.savingId !== null || !user.is_active}>삭제(비활성)</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {permissionUserId ? (() => {
        const user = users.find((item) => item.id === permissionUserId);
        const draft = drafts[permissionUserId];
        if (!user || !draft) return null;
        return (
          <div className="user-permission-modal-backdrop" role="presentation" onMouseDown={() => setPermissionUserId(null)}>
            <section className="user-permission-modal" role="dialog" aria-modal="true" aria-label={`${user.username} 메뉴 권한`} onMouseDown={(event) => event.stopPropagation()}>
              <div className="user-permission-modal-heading">
                <div><h3>{user.username} 메뉴 권한</h3><p>{draft.role === "admin" ? "admin은 모든 메뉴에 접근할 수 있습니다." : "허용할 메뉴를 선택하세요."}</p></div>
                <button type="button" className="ghost-button" onClick={() => setPermissionUserId(null)}>닫기</button>
              </div>
              <div className="user-permission-grid">
                {MENU_OPTIONS.map(([id, label]) => (
                  <label key={id}>
                    <input type="checkbox" checked={draft.role === "admin" || draft.menu_permissions.includes(id)} disabled={draft.role === "admin"} onChange={() => togglePermission(user.id, id)} />
                    {label}
                  </label>
                ))}
              </div>
              <div className="user-permission-modal-actions">
                <button type="button" onClick={async () => { await handleUpdate(user.id); setPermissionUserId(null); }}>권한 저장</button>
              </div>
            </section>
          </div>
        );
      })() : null}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ko-KR");
}

export default UserManagementPage;
