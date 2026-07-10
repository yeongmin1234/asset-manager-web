import React, { useEffect, useState } from "react";
import {
  createUser,
  deleteUser,
  getUsers,
  resetUserPassword,
  updateUser,
} from "../api/client.js";
import {
  haveSameMenuPermissions,
  MENU_PERMISSION_OPTIONS,
  normalizeMenuPermissions,
} from "../utils/menuPermissions.js";

const EMPTY_CREATE_FORM = {
  username: "",
  name: "",
  password: "",
  role: "user",
  menu_permissions: ["dashboard", "assets"],
};


function UserManagementPage({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [createForm, setCreateForm] = useState(EMPTY_CREATE_FORM);
  const [drafts, setDrafts] = useState({});
  const [resetPasswords, setResetPasswords] = useState({});
  const [permissionUserId, setPermissionUserId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [state, setState] = useState({ error: "", loading: true, message: "", savingId: null });

  const applyUsers = (items) => {
    setUsers(items);
    setDrafts(Object.fromEntries(items.map((user) => [
      user.id,
      {
        name: user.name,
        role: user.role,
        is_active: user.is_active,
        menu_permissions: normalizeMenuPermissions(user.menu_permissions) || [],
      },
    ])));
  };

  const loadUsers = async () => {
    setState((current) => ({ ...current, error: "", loading: true }));
    try {
      const items = await getUsers();
      applyUsers(items);
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
      const result = await action();
      if (result?.id) {
        setUsers((current) => current.map((user) => user.id === result.id ? result : user));
        setDrafts((current) => ({
          ...current,
          [result.id]: {
            name: result.name,
            role: result.role,
            is_active: result.is_active,
            menu_permissions: result.menu_permissions || [],
          },
        }));
      }
      await loadUsers();
      setState((current) => ({ ...current, loading: false, message: successMessage, savingId: null }));
      return result || true;
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

  const handleUpdate = async (userId, successMessage = "사용자 정보를 수정했습니다.") => {
    const draft = drafts[userId];
    const normalizedPermissions = normalizeMenuPermissions(draft?.menu_permissions);
    if (normalizedPermissions === null) {
      setState((current) => ({
        ...current,
        error: "메뉴 권한 요청값이 배열이 아닙니다.",
        message: "",
      }));
      return false;
    }
    const payload = { ...draft, menu_permissions: normalizedPermissions };
    setState((current) => ({ ...current, error: "", message: "", savingId: userId }));
    try {
      const savedUser = await updateUser(userId, payload);
      if (!savedUser || typeof savedUser !== "object" || Array.isArray(savedUser)) {
        throw new Error("사용자 저장 API가 응답 객체를 반환하지 않았습니다.");
      }
      if (!Array.isArray(savedUser.menu_permissions)) {
        throw new Error("사용자 저장 응답에 menu_permissions가 없습니다. Backend 배포 버전을 확인하세요.");
      }

      const refreshedUsers = await getUsers();
      if (!Array.isArray(refreshedUsers)) {
        throw new Error("사용자 목록 API가 배열을 반환하지 않았습니다.");
      }
      const persistedUser = refreshedUsers.find((user) => user.id === userId);
      if (!persistedUser) {
        throw new Error("저장 후 재조회한 사용자 목록에서 대상 사용자를 찾을 수 없습니다.");
      }
      if (!Array.isArray(persistedUser.menu_permissions)) {
        throw new Error("사용자 목록 응답에 menu_permissions가 없습니다. Backend 배포 버전을 확인하세요.");
      }

      const putMatches = haveSameMenuPermissions(savedUser.menu_permissions, payload.menu_permissions);
      const getMatches = Boolean(
        haveSameMenuPermissions(persistedUser.menu_permissions, payload.menu_permissions),
      );
      if (!putMatches || !getMatches) {
        throw new Error(
          !putMatches
            ? "저장 응답의 메뉴 권한이 요청값과 일치하지 않습니다."
            : "저장 후 재조회한 메뉴 권한이 요청값과 일치하지 않습니다.",
        );
      }
      applyUsers(refreshedUsers);
      setState((current) => ({
        ...current,
        loading: false,
        message: successMessage,
        savingId: null,
      }));
      return true;
    } catch (error) {
      setState((current) => ({
        ...current,
        error: formatApiError(error),
        savingId: null,
      }));
      return false;
    }
  };

  const handleResetPassword = async (userId) => {
    const password = resetPasswords[userId] || "";
    await runAction(
      () => resetUserPassword(userId, password),
      "비밀번호를 초기화했습니다.",
      userId,
    );
    setResetPasswords((current) => ({ ...current, [userId]: "" }));
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    const deletedId = deleteTarget.id;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    setState((current) => ({
      ...current,
      error: "",
      message: "",
      savingId: deletedId,
    }));
    try {
      const result = await deleteUser(deletedId);
      setUsers((current) => current.filter((user) => user.id !== deletedId));
      setDrafts((current) => omitKey(current, deletedId));
      setResetPasswords((current) => omitKey(current, deletedId));
      setDeleteTarget(null);
      setPermissionUserId((current) => current === deletedId ? null : current);
      window.requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));

      try {
        const refreshedUsers = await getUsers();
        if (refreshedUsers.some((user) => user.id === deletedId)) {
          throw new Error("삭제 API 호출 후에도 사용자 목록에 대상 계정이 남아 있습니다.");
        }
        applyUsers(refreshedUsers);
        setState((current) => ({
          ...current,
          loading: false,
          message: result?.message || "사용자 계정을 완전히 삭제했습니다.",
          savingId: null,
        }));
      } catch (refreshError) {
        setState((current) => ({
          ...current,
          error: `삭제 후 목록 재확인에 실패했습니다. ${formatApiError(refreshError)}`,
          savingId: null,
        }));
      }
    } catch (error) {
      setState((current) => ({
        ...current,
        error: formatApiError(error),
        savingId: null,
      }));
    }
  };

  const requestDelete = (user, protectionReason) => {
    setState((current) => ({ ...current, error: "", message: "" }));
    if (protectionReason) {
      setState((current) => ({ ...current, error: protectionReason }));
      return;
    }
    setDeleteTarget(user);
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
        <p>계정을 생성하고 권한, 활성 상태, 비밀번호와 계정 삭제를 관리합니다.</p>
      </div>

      <form className="user-create-panel" onSubmit={handleCreate}>
        <input placeholder="ID" value={createForm.username} onChange={(event) => setCreateForm({ ...createForm, username: event.target.value })} required />
        <input placeholder="이름" value={createForm.name} onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })} required />
        <input placeholder="비밀번호 (8자 이상)" type="password" minLength={8} autoComplete="new-password" value={createForm.password} onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })} required />
        <select value={createForm.role} onChange={(event) => setCreateForm({ ...createForm, role: event.target.value })}>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <button type="submit" className="user-create-submit" disabled={state.savingId !== null}>사용자 생성</button>
        <details className="user-create-permissions">
          <summary>기본 메뉴 권한</summary>
          <div className="user-permission-grid">
            {MENU_PERMISSION_OPTIONS.map(([id, label]) => (
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
              const adminCount = users.filter(
                (item) => item.role === "admin",
              ).length;
              const isCurrentUser = user.id === currentUser?.id;
              const isLastAdmin =
                user.role === "admin" && adminCount <= 1;
              const deleteProtectionReason = isCurrentUser
                ? "현재 로그인한 본인 계정은 삭제할 수 없습니다."
                : isLastAdmin
                  ? "마지막 관리자 계정은 삭제할 수 없습니다."
                  : "";
              const deleteTitle = deleteProtectionReason || "계정을 완전히 삭제합니다.";
              return (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td><input value={draft.name} onChange={(event) => updateDraft(user.id, "name", event.target.value)} /></td>
                  <td>
                    <div className="user-role-control">
                      <select value={draft.role} onChange={(event) => updateDraft(user.id, "role", event.target.value)}><option value="user">user</option><option value="admin">admin</option></select>
                      {draft.role === "admin" ? <span className="all-access-badge">전체 권한</span> : null}
                    </div>
                  </td>
                  <td><label className="user-status-toggle"><input type="checkbox" checked={draft.is_active} onChange={(event) => updateDraft(user.id, "is_active", event.target.checked)} /> {draft.is_active ? "활성" : "비활성"}</label></td>
                  <td>{formatDate(user.created_at)}</td>
                  <td>{formatDate(user.updated_at)}</td>
                  <td className="user-actions">
                    <button type="button" onClick={() => handleUpdate(user.id)} disabled={state.savingId !== null}>저장</button>
                    <button type="button" className="outline-button" onClick={() => setPermissionUserId(user.id)}>메뉴 권한</button>
                    <input type="password" minLength={8} autoComplete="new-password" placeholder="새 비밀번호" value={resetPasswords[user.id] || ""} onChange={(event) => setResetPasswords({ ...resetPasswords, [user.id]: event.target.value })} />
                    <button type="button" onClick={() => handleResetPassword(user.id)} disabled={state.savingId !== null || (resetPasswords[user.id] || "").length < 8}>초기화</button>
                    <button
                      type="button"
                      className={`danger-button${deleteProtectionReason ? " is-protected" : ""}`}
                      onClick={() => requestDelete(user, deleteProtectionReason)}
                      disabled={state.savingId !== null}
                      aria-disabled={Boolean(deleteProtectionReason)}
                      title={deleteTitle}
                    >
                      {state.savingId === user.id ? "삭제 중..." : "삭제"}
                    </button>
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
                {MENU_PERMISSION_OPTIONS.map(([id, label]) => (
                  <label key={id}>
                    <input type="checkbox" checked={draft.role === "admin" || draft.menu_permissions.includes(id)} disabled={draft.role === "admin"} onChange={() => togglePermission(user.id, id)} />
                    {label}
                  </label>
                ))}
              </div>
              <div className="user-permission-modal-actions">
                <button type="button" disabled={state.savingId !== null} onClick={async () => {
                  const saved = await handleUpdate(user.id, "메뉴 권한을 저장했습니다.");
                  if (saved) setPermissionUserId(null);
                }}>권한 저장</button>
              </div>
            </section>
          </div>
        );
      })() : null}
      {deleteTarget ? (
        <div className="user-permission-modal-backdrop" role="presentation" onMouseDown={() => {
          if (state.savingId === null) setDeleteTarget(null);
        }}>
          <section className="user-delete-modal" role="alertdialog" aria-modal="true" aria-labelledby="user-delete-title" onMouseDown={(event) => event.stopPropagation()}>
            <div>
              <h3 id="user-delete-title">사용자 계정 완전 삭제</h3>
              <p>
                ID ‘<strong>{deleteTarget.username}</strong>’ 계정을 완전히 삭제하시겠습니까?
                <br />
                삭제 후 복구할 수 없습니다.
              </p>
            </div>
            <div className="user-delete-modal-actions">
              <button type="button" className="ghost-button" onClick={() => setDeleteTarget(null)} disabled={state.savingId !== null}>취소</button>
              <button type="button" className="danger-button" onClick={handleDelete} disabled={state.savingId !== null}>
                {state.savingId === deleteTarget.id ? "삭제 중..." : "완전 삭제"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ko-KR");
}

function formatApiError(error) {
  const statusText = error?.status ? `HTTP ${error.status}: ` : "";
  return `${statusText}${error?.message || "요청 처리 중 오류가 발생했습니다."}`;
}

function omitKey(object, key) {
  const next = { ...object };
  delete next[key];
  return next;
}

export default UserManagementPage;
