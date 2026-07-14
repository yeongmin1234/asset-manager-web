import React, { useCallback, useEffect, useMemo, useState } from "react";
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
  const { columnWidths, handleColumnResizeStart, resetColumnWidths, tableWidth } = useResizableColumns(
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
      else await createHrAccount(form);
      setEditing(null);
      setIsFormOpen(false);
      setForm(EMPTY_FORM);
      await loadItems();
      setState((value) => ({ ...value, saving: false, message: editing ? "수정했습니다." : "등록했습니다." }));
    } catch (error) {
      setState((value) => ({ ...value, saving: false, error: error.message }));
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
          <button type="submit">검색</button>
          <button type="button" onClick={() => { setKeyword(""); setAppliedKeyword(""); }}>초기화</button>
        </form>
        <button type="button" onClick={resetColumnWidths}>컬럼 너비 초기화</button>
      </div>
      {state.message ? <p className="hr-account-message">{state.message}</p> : null}
      {state.error ? <p className="hr-account-error">{state.error}</p> : null}
      <div className="content-panel hr-account-table-panel">
        <div className="hr-account-table-wrap">
          <table className="hr-account-table" style={{ width: tableWidth + (isAdmin ? 120 : 0) }}>
            <colgroup>{colgroup}{isAdmin ? <col style={{ width: 120 }} /> : null}</colgroup>
            <thead><tr>{COLUMNS.map((column) => (
              <th key={column.key}><div className="resizable-table-heading"><span>{column.label}</span><button type="button" className="table-column-resize-handle" aria-label={`${column.label} 너비 조절`} onMouseDown={(event) => handleColumnResizeStart(event, column)} /></div></th>
            ))}{isAdmin ? <th>관리</th> : null}</tr></thead>
            <tbody>
              {state.loading ? <tr><td colSpan={COLUMNS.length + (isAdmin ? 1 : 0)}>불러오는 중...</td></tr> : null}
              {!state.loading && items.length === 0 ? <tr><td colSpan={COLUMNS.length + (isAdmin ? 1 : 0)}>등록된 계정 현황이 없습니다.</td></tr> : null}
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
