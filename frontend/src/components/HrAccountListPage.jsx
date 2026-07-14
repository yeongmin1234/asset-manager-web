import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createHrAccount, deleteHrAccount, getHrAccounts, updateHrAccount } from "../api/client.js";
import useResizableColumns from "../hooks/useResizableColumns.js";

const EMPTY_FORM = { department: "", name: "", dowoffice: "", erp: "", scm: "", nas: "" };
const COLUMNS = [
  { key: "department", label: "부서", initialWidth: 150, minWidth: 90 },
  { key: "name", label: "이름", initialWidth: 130, minWidth: 80 },
  { key: "dowoffice", label: "다우오피스", initialWidth: 180, minWidth: 110 },
  { key: "erp", label: "ERP", initialWidth: 160, minWidth: 100 },
  { key: "scm", label: "SCM", initialWidth: 160, minWidth: 100 },
  { key: "nas", label: "NAS", initialWidth: 160, minWidth: 100 },
  { key: "created_at", label: "생성날짜", initialWidth: 170, minWidth: 130 },
];

export default function HrAccountListPage({ currentUser }) {
  const isAdmin = currentUser?.role === "admin";
  const [items, setItems] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [state, setState] = useState({ loading: true, saving: false, error: "", message: "" });
  const [editing, setEditing] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [quickForm, setQuickForm] = useState(EMPTY_FORM);
  const [quickState, setQuickState] = useState({ saving: false, error: "", message: "", missingFields: [] });
  const quickDepartmentRef = useRef(null);
  const quickSavingRef = useRef(false);
  const { columnWidths, handleColumnResizeStart, tableWidth } = useResizableColumns(
    COLUMNS, "assetManager.hrAccounts.columnWidths", "hr-column-resizing",
  );

  const loadItems = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      setItems(await getHrAccounts({ keyword: appliedKeyword }));
      setState((value) => ({ ...value, loading: false }));
    } catch (error) {
      setState((value) => ({ ...value, loading: false, error: error.message }));
    }
  }, [appliedKeyword]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const createAccountAndReload = useCallback(async (payload) => {
    await createHrAccount(payload);
    await loadItems();
  }, [loadItems]);

  const openForm = (item = null) => {
    setIsFormOpen(true);
    setEditing(item);
    setForm(item ? Object.fromEntries(Object.keys(EMPTY_FORM).map((key) => [key, item[key] || ""])) : EMPTY_FORM);
    setState((value) => ({ ...value, error: "", message: "" }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setState((value) => ({ ...value, saving: true, error: "", message: "" }));
    try {
      if (editing) await updateHrAccount(editing.id, form);
      else await createAccountAndReload(form);
      setEditing(null);
      setIsFormOpen(false);
      setForm(EMPTY_FORM);
      if (editing) await loadItems();
      setState((value) => ({ ...value, saving: false, message: editing ? "수정했습니다." : "등록했습니다." }));
    } catch (error) {
      setState((value) => ({ ...value, saving: false, error: error.message }));
    }
  };

  const submitQuickForm = async (event) => {
    event.preventDefault();
    if (quickSavingRef.current) return;

    const normalizedForm = Object.fromEntries(
      Object.entries(quickForm).map(([key, value]) => [key, value.trim()]),
    );
    const missingFields = ["department", "name"].filter((key) => !normalizedForm[key]);
    if (missingFields.length) {
      setQuickState({ saving: false, error: "부서와 이름을 입력해주세요.", message: "", missingFields });
      return;
    }

    quickSavingRef.current = true;
    setQuickState({ saving: true, error: "", message: "", missingFields: [] });
    try {
      await createAccountAndReload(normalizedForm);
      setQuickForm(EMPTY_FORM);
      setQuickState({ saving: false, error: "", message: "등록했습니다.", missingFields: [] });
      window.requestAnimationFrame(() => quickDepartmentRef.current?.focus());
    } catch (error) {
      setQuickState({
        saving: false,
        error: formatQuickError(error),
        message: "",
        missingFields: [],
      });
    } finally {
      quickSavingRef.current = false;
    }
  };

  const remove = async (item) => {
    if (!window.confirm(`${item.name} 계정 현황을 삭제하시겠습니까?`)) return;
    try {
      await deleteHrAccount(item.id);
      await loadItems();
      setState((value) => ({ ...value, message: "삭제했습니다.", error: "" }));
    } catch (error) {
      setState((value) => ({ ...value, error: error.message }));
    }
  };

  const colgroup = useMemo(() => COLUMNS.map((column) => (
    <col key={column.key} style={{ width: columnWidths[column.key] }} />
  )), [columnWidths]);

  return (
    <section className="hr-account-page">
      <div className="portal-screen-heading hr-account-heading">
        <div><h2>인사업무 리스트</h2><p>구성원별 주요 시스템 계정 보유 현황을 관리합니다.</p></div>
        {isAdmin ? <button type="button" className="hr-primary-button" onClick={() => openForm()}>신규 등록</button> : null}
      </div>
      <div className="content-panel hr-account-toolbar">
        <form onSubmit={(event) => { event.preventDefault(); setAppliedKeyword(keyword.trim()); }}>
          <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="부서, 이름, 시스템 계정 검색" aria-label="계정 현황 검색" />
          <button type="submit" className="secondary-button">검색</button>
          <button type="button" className="secondary-button" onClick={() => { setKeyword(""); setAppliedKeyword(""); }}>초기화</button>
        </form>
      </div>
      {isAdmin ? (
        <div className="content-panel hr-account-quick-panel">
          <form
            className="hr-account-quick-form"
            onSubmit={submitQuickForm}
            onKeyDown={(event) => { if (event.nativeEvent.isComposing) event.preventDefault(); }}
          >
            {Object.entries({ department: "부서", name: "이름", dowoffice: "다우오피스", erp: "ERP", scm: "SCM", nas: "NAS" }).map(([key, label], index) => (
              <input
                key={key}
                ref={index === 0 ? quickDepartmentRef : undefined}
                value={quickForm[key]}
                maxLength={key === "department" || key === "name" ? 100 : 200}
                placeholder={`${label}${key === "department" || key === "name" ? " *" : ""}`}
                aria-label={`${label} 간편등록`}
                aria-invalid={quickState.missingFields.includes(key)}
                className={quickState.missingFields.includes(key) ? "is-invalid" : ""}
                disabled={quickState.saving}
                onChange={(event) => {
                  setQuickForm((value) => ({ ...value, [key]: event.target.value }));
                  setQuickState((value) => ({ ...value, error: "", message: "", missingFields: value.missingFields.filter((field) => field !== key) }));
                }}
              />
            ))}
            <button type="submit" className="hr-primary-button" disabled={quickState.saving}>
              {quickState.saving ? "등록 중..." : "등록"}
            </button>
          </form>
          {quickState.message ? <p className="hr-account-quick-message is-success">{quickState.message}</p> : null}
          {quickState.error ? <p className="hr-account-quick-message is-error">{quickState.error}</p> : null}
        </div>
      ) : null}
      {state.message ? <p className="hr-account-message">{state.message}</p> : null}
      {state.error ? <p className="hr-account-error">{state.error}</p> : null}
      <div className="content-panel hr-account-table-panel">
        <div className="hr-account-table-wrap">
          <table className="hr-account-table" style={{ width: `max(100%, ${tableWidth + (isAdmin ? 120 : 0)}px)` }}>
            <colgroup>{colgroup}{isAdmin ? <col style={{ width: 120 }} /> : null}</colgroup>
            <thead><tr>{COLUMNS.map((column) => (
              <th key={column.key}><div className="resizable-table-heading"><span>{column.label}</span><button type="button" className="table-column-resize-handle" aria-label={`${column.label} 너비 조절`} onMouseDown={(event) => handleColumnResizeStart(event, column)} /></div></th>
            ))}{isAdmin ? <th>관리</th> : null}</tr></thead>
            <tbody>
              {state.loading ? <tr><td colSpan={COLUMNS.length + (isAdmin ? 1 : 0)}>불러오는 중...</td></tr> : null}
              {!state.loading && items.length === 0 ? <tr className="hr-account-empty-row"><td colSpan={COLUMNS.length + (isAdmin ? 1 : 0)}>등록된 계정 현황이 없습니다.</td></tr> : null}
              {!state.loading && items.map((item) => <tr key={item.id}>
                <td>{item.department}</td><td>{item.name}</td><td>{item.dowoffice || "-"}</td><td>{item.erp || "-"}</td><td>{item.scm || "-"}</td><td>{item.nas || "-"}</td><td>{formatDate(item.created_at)}</td>
                {isAdmin ? <td><div className="hr-account-actions"><button type="button" onClick={() => openForm(item)}>수정</button><button type="button" className="danger-button" onClick={() => remove(item)}>삭제</button></div></td> : null}
              </tr>)}
            </tbody>
          </table>
        </div>
      </div>
      {isFormOpen ? <div className="hr-account-modal-backdrop" role="presentation" onMouseDown={() => { setIsFormOpen(false); setEditing(null); setForm(EMPTY_FORM); }}>
        <form className="hr-account-modal" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
          <div className="hr-account-modal-heading"><div><h3>{editing ? "계정 현황 수정" : "계정 현황 등록"}</h3><p>생성날짜는 저장 시 자동으로 기록됩니다.</p></div><button type="button" onClick={() => { setIsFormOpen(false); setEditing(null); setForm(EMPTY_FORM); }}>닫기</button></div>
          <div className="hr-account-form-grid">{Object.entries({ department: "부서", name: "이름", dowoffice: "다우오피스", erp: "ERP", scm: "SCM", nas: "NAS" }).map(([key, label]) => <label key={key}><span>{label}{["department", "name"].includes(key) ? " *" : ""}</span><input value={form[key]} required={["department", "name"].includes(key)} maxLength={key === "department" || key === "name" ? 100 : 200} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}</div>
          <div className="hr-account-modal-actions"><button type="button" onClick={() => { setIsFormOpen(false); setEditing(null); setForm(EMPTY_FORM); }}>취소</button><button type="submit" className="hr-primary-button" disabled={state.saving}>{state.saving ? "저장 중..." : "저장"}</button></div>
        </form>
      </div> : null}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ko-KR");
}

function formatQuickError(error) {
  if (error?.status === 409) return "이미 등록된 계정 정보입니다.";
  if (error?.status >= 500) return "서버 오류로 등록하지 못했습니다. 잠시 후 다시 시도해주세요.";
  return error?.message || "등록하지 못했습니다. 입력값을 확인해주세요.";
}
