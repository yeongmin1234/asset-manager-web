import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  commitHrAccountExcelImport, createHrAccount, deleteHrAccount,
  downloadHrAccountImportTemplate, getHrAccounts, previewHrAccountExcelImport,
  updateHrAccount,
} from "../api/client.js";
import useResizableColumns from "../hooks/useResizableColumns.js";
import { HR_EXCEL_IMPORT_TARGET, recordMenuAccessBestEffort } from "../hooks/useMenuAccessLog.js";

const EMPTY_FORM = { department: "", name: "", dowoffice: "", erp: "", scm: "", nas: "" };
const FILTERABLE_COLUMNS = ["department", "name", "dowoffice", "erp", "scm", "nas"];
const EMPTY_EXCEL_FILTERS = Object.fromEntries([...FILTERABLE_COLUMNS, "created_at"].map((key) => [key, null]));
const HR_TABLE_VIEW_STORAGE_KEY = "assetManager.hrAccounts.tableView";
const COLUMNS = [
  { key: "department", label: "부서", initialWidth: 144, minWidth: 100 },
  { key: "name", label: "이름", initialWidth: 132, minWidth: 90 },
  { key: "dowoffice", label: "다우오피스", initialWidth: 156, minWidth: 110 },
  { key: "erp", label: "ERP", initialWidth: 156, minWidth: 100 },
  { key: "scm", label: "SCM", initialWidth: 156, minWidth: 100 },
  { key: "nas", label: "NAS", initialWidth: 156, minWidth: 100 },
  { key: "created_at", label: "생성날짜", initialWidth: 180, minWidth: 140 },
];
const MANAGEMENT_COLUMN = { key: "actions", label: "관리", initialWidth: 150, minWidth: 150 };
const ADMIN_COLUMNS = [...COLUMNS, MANAGEMENT_COLUMN];
const MAX_EXCEL_FILE_SIZE = 5 * 1024 * 1024;
const EMPTY_EXCEL_STATE = {
  isOpen: false, loading: false, saving: false, fileName: "", error: "",
  preview: null, duplicatePolicy: "skip", result: null,
};

export default function HrAccountListPage({ currentUser }) {
  const isAdmin = currentUser?.role === "admin";
  const [items, setItems] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [state, setState] = useState({ loading: true, saving: false, error: "", message: "" });
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const initialTableView = useMemo(loadHrTableView, []);
  const [excelFilters, setExcelFilters] = useState(initialTableView.filters);
  const [sortState, setSortState] = useState(initialTableView.sort);
  const [openFilter, setOpenFilter] = useState(null);
  const [filterSearch, setFilterSearch] = useState("");
  const [draftSelectedValues, setDraftSelectedValues] = useState([]);
  const [draftDateFilter, setDraftDateFilter] = useState({ mode: "all", start: "", end: "" });
  const [inlineState, setInlineState] = useState({ saving: false, error: "", missingFields: [] });
  const [quickForm, setQuickForm] = useState(EMPTY_FORM);
  const [quickState, setQuickState] = useState({ saving: false, error: "", message: "", missingFields: [] });
  const [excelState, setExcelState] = useState(EMPTY_EXCEL_STATE);
  const quickDepartmentRef = useRef(null);
  const quickSavingRef = useRef(false);
  const inlineSavingRef = useRef(false);
  const excelFileInputRef = useRef(null);
  const filterPopoverRef = useRef(null);
  const tableColumns = isAdmin ? ADMIN_COLUMNS : COLUMNS;
  const { columnWidths, handleColumnResizeStart, tableWidth } = useResizableColumns(
    tableColumns, "assetManager.hrAccounts.columnWidths", "hr-column-resizing",
  );

  const loadItems = useCallback(async () => {
    setState((value) => ({ ...value, loading: true, error: "" }));
    try {
      setItems(await getHrAccounts({ keyword: appliedKeyword }));
      setState((value) => ({ ...value, loading: false }));
    } catch (error) {
      setState((value) => ({ ...value, loading: false, error: formatHrApiError(error, "목록을 불러오지 못했습니다.") }));
    }
  }, [appliedKeyword]);

  useEffect(() => { loadItems(); }, [loadItems]);

  useEffect(() => {
    window.sessionStorage.setItem(HR_TABLE_VIEW_STORAGE_KEY, JSON.stringify({ filters: excelFilters, sort: sortState }));
  }, [excelFilters, sortState]);

  useEffect(() => {
    if (!openFilter) return undefined;
    const closeOnOutsideClick = (event) => {
      if (!filterPopoverRef.current?.contains(event.target) && !event.target.closest?.(".hr-account-filter-button")) setOpenFilter(null);
    };
    const closeOnEscape = (event) => { if (event.key === "Escape") setOpenFilter(null); };
    const closeOnViewportChange = (event) => {
      if (event.type === "scroll" && filterPopoverRef.current?.contains(event.target)) return;
      setOpenFilter(null);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    window.addEventListener("resize", closeOnViewportChange);
    window.addEventListener("scroll", closeOnViewportChange, true);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
      window.removeEventListener("resize", closeOnViewportChange);
      window.removeEventListener("scroll", closeOnViewportChange, true);
    };
  }, [openFilter]);

  const createAccountAndReload = useCallback(async (payload) => {
    await createHrAccount(payload);
    await loadItems();
  }, [loadItems]);

  const beginInlineEdit = (item) => {
    if (inlineSavingRef.current || editing?.id === item.id) return;
    if (editing && hasInlineChanges(editing, form) && !window.confirm("수정 중인 내용이 있습니다. 취소하고 다른 행을 수정하시겠습니까?")) return;
    setEditing(item);
    setForm(Object.fromEntries(Object.keys(EMPTY_FORM).map((key) => [key, item[key] || ""])));
    setInlineState({ saving: false, error: "", missingFields: [] });
    setState((value) => ({ ...value, error: "", message: "" }));
  };

  const cancelInlineEdit = () => {
    if (inlineSavingRef.current) return;
    setEditing(null);
    setForm(EMPTY_FORM);
    setInlineState({ saving: false, error: "", missingFields: [] });
  };

  const saveInlineEdit = async () => {
    if (!editing || inlineSavingRef.current) return;
    const normalizedForm = Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value.trim()]));
    const missingFields = ["department", "name"].filter((key) => !normalizedForm[key]);
    if (missingFields.length) {
      setInlineState({ saving: false, error: "부서와 이름을 입력해주세요.", missingFields });
      return;
    }
    inlineSavingRef.current = true;
    setInlineState({ saving: true, error: "", missingFields: [] });
    try {
      const updated = await updateHrAccount(editing.id, normalizedForm);
      setItems((value) => value.map((item) => item.id === updated.id ? updated : item));
      setEditing(null);
      setForm(EMPTY_FORM);
      setInlineState({ saving: false, error: "", missingFields: [] });
      setState((value) => ({ ...value, error: "", message: "수정했습니다." }));
    } catch (error) {
      setInlineState({ saving: false, error: formatHrApiError(error, "수정에 실패했습니다."), missingFields: [] });
    } finally {
      inlineSavingRef.current = false;
    }
  };

  const handleInlineKeyDown = (event) => {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Enter") {
      event.preventDefault();
      saveInlineEdit();
    } else if (event.key === "Escape") {
      event.preventDefault();
      cancelInlineEdit();
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
      setState((value) => ({ ...value, error: formatHrApiError(error, "삭제에 실패했습니다.") }));
    }
  };

  const selectExcelFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      setExcelState({ ...EMPTY_EXCEL_STATE, error: "엑셀 통합 문서(.xlsx) 파일만 선택할 수 있습니다." });
      event.target.value = "";
      return;
    }
    if (file.size > MAX_EXCEL_FILE_SIZE) {
      setExcelState({ ...EMPTY_EXCEL_STATE, error: "엑셀 파일은 최대 5MB까지 선택할 수 있습니다." });
      event.target.value = "";
      return;
    }
    setExcelState({ ...EMPTY_EXCEL_STATE, isOpen: true, loading: true, fileName: file.name });
    try {
      const preview = await previewHrAccountExcelImport(file);
      setExcelState((value) => ({ ...value, loading: false, preview }));
    } catch (error) {
      setExcelState((value) => ({ ...value, loading: false, error: formatExcelError(error, "엑셀 파일을 분석하지 못했습니다.") }));
    } finally {
      event.target.value = "";
    }
  };

  const closeExcelModal = () => {
    if (excelState.loading || excelState.saving) return;
    setExcelState(EMPTY_EXCEL_STATE);
  };

  const commitExcelImport = async () => {
    if (!excelState.preview || excelState.saving) return;
    setExcelState((value) => ({ ...value, saving: true, error: "", result: null }));
    try {
      const result = await commitHrAccountExcelImport(excelState.preview.rows, excelState.duplicatePolicy);
      await loadItems();
      setExcelState((value) => ({ ...value, saving: false, result }));
    } catch (error) {
      setExcelState((value) => ({ ...value, saving: false, error: formatExcelError(error, "엑셀 일괄등록에 실패했습니다.") }));
    }
  };

  const downloadExcelTemplate = async () => {
    try {
      const { blob, filename } = await downloadHrAccountImportTemplate();
      saveDownload(blob, filename || "인사업무_계정등록_양식.xlsx");
    } catch (error) {
      setExcelState((value) => ({ ...value, error: formatExcelError(error, "엑셀 양식을 내려받지 못했습니다.") }));
    }
  };

  const uniqueValuesByColumn = useMemo(() => Object.fromEntries(FILTERABLE_COLUMNS.map((key) => [
    key,
    [...new Set(items.map((item) => normalizeFilterValue(item[key])))].sort(compareFilterValues),
  ])), [items]);

  const showFilterPopover = (event, column) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setFilterSearch("");
    if (column.key === "created_at") {
      setDraftDateFilter(excelFilters.created_at || { mode: "all", start: "", end: "" });
    } else {
      setDraftSelectedValues(excelFilters[column.key] || uniqueValuesByColumn[column.key]);
    }
    setOpenFilter({
      key: column.key,
      label: column.label,
      left: Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - 288)),
      top: rect.bottom + 430 > window.innerHeight ? Math.max(8, rect.top - 425) : rect.bottom + 5,
    });
  };

  const filteredDraftValues = useMemo(() => {
    if (!openFilter || openFilter.key === "created_at") return [];
    const search = filterSearch.trim().toLocaleLowerCase();
    return uniqueValuesByColumn[openFilter.key].filter((value) => !search || filterValueLabel(value).toLocaleLowerCase().includes(search));
  }, [filterSearch, openFilter, uniqueValuesByColumn]);

  const toggleAllDraftValues = (checked) => {
    setDraftSelectedValues(checked ? [...uniqueValuesByColumn[openFilter.key]] : []);
  };

  const toggleDraftValue = (value) => {
    setDraftSelectedValues((selected) => selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  };

  const applyOpenFilter = () => {
    if (!openFilter) return;
    if (openFilter.key === "created_at") {
      const nextDateFilter = draftDateFilter.mode === "all" ? null : draftDateFilter;
      setExcelFilters((value) => ({ ...value, created_at: nextDateFilter }));
    } else {
      const allValues = uniqueValuesByColumn[openFilter.key];
      const selected = allValues.filter((value) => draftSelectedValues.includes(value));
      setExcelFilters((value) => ({ ...value, [openFilter.key]: selected.length === allValues.length ? null : selected }));
    }
    setOpenFilter(null);
  };

  const resetOpenFilter = () => {
    if (!openFilter) return;
    setExcelFilters((value) => ({ ...value, [openFilter.key]: null }));
    setSortState((value) => value.key === openFilter.key ? { key: null, direction: null } : value);
    setOpenFilter(null);
  };

  const resetSearchAndFilters = () => {
    setKeyword("");
    setAppliedKeyword("");
    setExcelFilters(EMPTY_EXCEL_FILTERS);
    setSortState({ key: null, direction: null });
    setOpenFilter(null);
  };

  const visibleItems = useMemo(() => items
    .filter((item) => item.id === editing?.id || matchesExcelFilters(item, excelFilters))
    .sort((left, right) => compareHrItems(left, right, sortState)), [editing?.id, excelFilters, items, sortState]);

  const colgroup = useMemo(() => tableColumns.map((column) => (
    <col key={column.key} style={{ width: columnWidths[column.key] }} />
  )), [columnWidths, tableColumns]);
  const openFilterValues = openFilter?.key && openFilter.key !== "created_at" ? uniqueValuesByColumn[openFilter.key] : [];
  const allDraftValuesSelected = openFilterValues.length > 0 && draftSelectedValues.length === openFilterValues.length;
  const someDraftValuesSelected = draftSelectedValues.length > 0 && !allDraftValuesSelected;
  const invalidCustomDateRange = draftDateFilter.mode === "custom" && draftDateFilter.start && draftDateFilter.end && draftDateFilter.start > draftDateFilter.end;

  return (
    <section className="hr-account-page">
      <div className="portal-screen-heading hr-account-heading">
        <div><h2>인사업무 리스트</h2><p>구성원별 주요 시스템 계정 보유 현황을 관리합니다.</p></div>
        {isAdmin ? (
          <div className="hr-account-excel-attachment">
            <input
              ref={excelFileInputRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={selectExcelFile}
              tabIndex={-1}
              aria-hidden="true"
            />
            <button type="button" className="hr-account-excel-button" onClick={() => {
              recordMenuAccessBestEffort(HR_EXCEL_IMPORT_TARGET);
              excelFileInputRef.current?.click();
            }}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 2.5L17.5 8H14ZM8 12l2 3-2 3h2l1-1.7 1 1.7h2l-2-3 2-3h-2l-1 1.7-1-1.7Z" /></svg>
              엑셀 일괄등록
            </button>
            {excelState.error && !excelState.isOpen ? <span className="hr-account-excel-error" role="alert">{excelState.error}</span> : null}
          </div>
        ) : null}
      </div>
      <div className="content-panel hr-account-toolbar">
        <form onSubmit={(event) => { event.preventDefault(); setAppliedKeyword(keyword.trim()); }}>
          <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="부서, 이름, 시스템 계정 검색" aria-label="계정 현황 검색" />
          <button type="submit" className="secondary-button">검색</button>
          <button type="button" className="secondary-button" onClick={resetSearchAndFilters}>초기화</button>
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
          <table className="hr-account-table" style={{ width: `max(100%, ${tableWidth}px)` }}>
            <colgroup>{colgroup}</colgroup>
            <thead>
              <tr className="hr-account-header-row">{tableColumns.map((column) => (
                <th key={column.key}><div className="resizable-table-heading"><span>{column.label}</span>{column.key !== "actions" ? (
                  <button
                    type="button"
                    className={`hr-account-filter-button${excelFilters[column.key] !== null ? " is-filtered" : ""}${sortState.key === column.key ? " is-sorted" : ""}`}
                    aria-label={`${column.label} 필터 및 정렬`}
                    aria-expanded={openFilter?.key === column.key}
                    onMouseDown={(event) => event.stopPropagation()}
                    onClick={(event) => showFilterPopover(event, column)}
                  ><span aria-hidden="true">▼</span></button>
                ) : null}<button type="button" className="table-column-resize-handle" aria-label={`${column.label} 너비 조절`} onMouseDown={(event) => handleColumnResizeStart(event, column)} /></div></th>
              ))}</tr>
            </thead>
            <tbody>
              {state.loading ? <tr><td colSpan={tableColumns.length}>불러오는 중...</td></tr> : null}
              {!state.loading && visibleItems.length === 0 ? <tr className="hr-account-empty-row"><td colSpan={tableColumns.length}>{items.length ? "필터 조건에 맞는 계정 현황이 없습니다." : "등록된 계정 현황이 없습니다."}</td></tr> : null}
              {!state.loading && visibleItems.map((item) => {
                const isEditing = editing?.id === item.id;
                return <React.Fragment key={item.id}>
                  <tr className={isEditing ? "hr-account-editing-row" : undefined}>
                    {Object.keys(EMPTY_FORM).map((key) => <td key={key}>{isEditing ? (
                      <input
                        className={`hr-account-inline-input${inlineState.missingFields.includes(key) ? " is-invalid" : ""}`}
                        value={form[key]}
                        maxLength={key === "department" || key === "name" ? 100 : 200}
                        aria-label={`${COLUMNS.find((column) => column.key === key)?.label || key} 수정`}
                        aria-invalid={inlineState.missingFields.includes(key)}
                        disabled={inlineState.saving}
                        onKeyDown={handleInlineKeyDown}
                        onChange={(event) => {
                          setForm((value) => ({ ...value, [key]: event.target.value }));
                          setInlineState((value) => ({ ...value, error: "", missingFields: value.missingFields.filter((field) => field !== key) }));
                        }}
                      />
                    ) : (item[key] || "-")}</td>)}
                    <td>{formatDate(item.created_at)}</td>
                    {isAdmin ? <td className="hr-account-actions-cell"><div className="hr-account-actions">
                      {isEditing ? <><button type="button" className="hr-account-save-button" onClick={saveInlineEdit} disabled={inlineState.saving}>{inlineState.saving ? "저장 중" : "저장"}</button><button type="button" onClick={cancelInlineEdit} disabled={inlineState.saving}>취소</button></> : <><button type="button" className="hr-account-edit-button" onClick={() => beginInlineEdit(item)}>수정</button><button type="button" className="danger-button" onClick={() => remove(item)}>삭제</button></>}
                    </div></td> : null}
                  </tr>
                  {isEditing && inlineState.error ? <tr className="hr-account-inline-error-row"><td colSpan={tableColumns.length}>{inlineState.error}</td></tr> : null}
                </React.Fragment>;
              })}
            </tbody>
          </table>
        </div>
      </div>
      {openFilter ? (
        <div ref={filterPopoverRef} className="hr-account-filter-popover" style={{ left: openFilter.left, top: openFilter.top }} role="dialog" aria-label={`${openFilter.label} 필터`}>
          <div className="hr-account-filter-popover-title"><strong>{openFilter.label}</strong><span>필터 및 정렬</span></div>
          <div className="hr-account-filter-sort-actions">
            <button type="button" className={sortState.key === openFilter.key && sortState.direction === "asc" ? "is-active" : ""} onClick={() => setSortState({ key: openFilter.key, direction: "asc" })}>{openFilter.key === "created_at" ? "오래된순" : "오름차순"}</button>
            <button type="button" className={sortState.key === openFilter.key && sortState.direction === "desc" ? "is-active" : ""} onClick={() => setSortState({ key: openFilter.key, direction: "desc" })}>{openFilter.key === "created_at" ? "최신순" : "내림차순"}</button>
          </div>
          {openFilter.key === "created_at" ? (
            <div className="hr-account-date-filter-options">
              {[
                ["all", "전체"], ["today", "오늘"], ["last7", "최근 7일"],
                ["last30", "최근 30일"], ["custom", "사용자 지정 기간"],
              ].map(([mode, label]) => <label key={mode}><input type="radio" name="hr-created-date-filter" value={mode} checked={draftDateFilter.mode === mode} onChange={() => setDraftDateFilter((value) => ({ ...value, mode }))} /> {label}</label>)}
              {draftDateFilter.mode === "custom" ? <div className="hr-account-custom-date-range">
                <label><span>시작일</span><input type="date" value={draftDateFilter.start} max={draftDateFilter.end || undefined} onChange={(event) => setDraftDateFilter((value) => ({ ...value, start: event.target.value }))} /></label>
                <label><span>종료일</span><input type="date" value={draftDateFilter.end} min={draftDateFilter.start || undefined} onChange={(event) => setDraftDateFilter((value) => ({ ...value, end: event.target.value }))} /></label>
                {invalidCustomDateRange ? <p>시작일은 종료일보다 늦을 수 없습니다.</p> : null}
              </div> : null}
            </div>
          ) : (
            <>
              <input className="hr-account-filter-value-search" type="search" value={filterSearch} placeholder={`${openFilter.label} 값 검색`} onChange={(event) => setFilterSearch(event.target.value)} autoFocus />
              <div className="hr-account-filter-value-list">
                <label className="hr-account-filter-select-all"><input type="checkbox" checked={allDraftValuesSelected} ref={(element) => { if (element) element.indeterminate = someDraftValuesSelected; }} onChange={(event) => toggleAllDraftValues(event.target.checked)} /> 전체 선택</label>
                {filteredDraftValues.map((value) => <label key={value || "__empty__"}><input type="checkbox" checked={draftSelectedValues.includes(value)} onChange={() => toggleDraftValue(value)} /><span title={filterValueLabel(value)}>{filterValueLabel(value)}</span></label>)}
                {filteredDraftValues.length === 0 ? <p className="hr-account-filter-no-values">검색 결과가 없습니다.</p> : null}
              </div>
            </>
          )}
          <div className="hr-account-filter-popover-actions"><button type="button" onClick={resetOpenFilter}>초기화</button><button type="button" className="hr-account-filter-apply" onClick={applyOpenFilter} disabled={invalidCustomDateRange}>적용</button></div>
        </div>
      ) : null}
      {excelState.isOpen ? (
        <div className="hr-account-modal-backdrop hr-account-import-backdrop" role="presentation" onMouseDown={closeExcelModal}>
          <section className="hr-account-modal hr-account-import-modal" role="dialog" aria-modal="true" aria-labelledby="hr-import-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="hr-account-modal-heading hr-account-import-heading">
              <div><h3 id="hr-import-title">엑셀 일괄등록</h3><p>{excelState.fileName || "선택한 파일의 첫 번째 시트를 분석합니다."}</p></div>
              <div className="hr-account-import-heading-actions">
                <button type="button" onClick={downloadExcelTemplate}>엑셀 양식 다운로드</button>
                <button type="button" onClick={() => excelFileInputRef.current?.click()} disabled={excelState.loading || excelState.saving}>파일 다시 선택</button>
                <button type="button" onClick={closeExcelModal} disabled={excelState.loading || excelState.saving}>닫기</button>
              </div>
            </div>

            {excelState.loading ? <div className="hr-account-import-loading">엑셀 컬럼과 데이터를 분석하고 있습니다...</div> : null}
            {excelState.error ? <p className="hr-account-import-error" role="alert">{excelState.error}</p> : null}
            {excelState.preview ? (
              <>
                <div className="hr-account-import-summary">
                  <span>전체 <strong>{excelState.preview.total_count}</strong>건</span>
                  <span className="is-valid">정상 <strong>{excelState.preview.valid_count}</strong>건</span>
                  <span className="is-duplicate">중복 <strong>{excelState.preview.duplicate_count}</strong>건</span>
                  <span className="is-error">오류 <strong>{excelState.preview.error_count}</strong>건</span>
                </div>
                <div className="hr-account-import-mapping">
                  {Object.entries({ department: "부서", name: "이름", dowoffice: "다우오피스", erp: "ERP", scm: "SCM", nas: "NAS" }).map(([key, label]) => (
                    <span key={key}><strong>{label}</strong> ← {excelState.preview.matched_columns[key] || "미매칭(선택)"}</span>
                  ))}
                </div>
                <fieldset className="hr-account-import-policy">
                  <legend>중복 처리 방식</legend>
                  <label><input type="radio" name="hr-duplicate-policy" value="skip" checked={excelState.duplicatePolicy === "skip"} onChange={() => setExcelState((value) => ({ ...value, duplicatePolicy: "skip", result: null }))} /> 중복 건 건너뛰기</label>
                  <label><input type="radio" name="hr-duplicate-policy" value="update" checked={excelState.duplicatePolicy === "update"} onChange={() => setExcelState((value) => ({ ...value, duplicatePolicy: "update", result: null }))} /> 기존 데이터 업데이트</label>
                </fieldset>
                <div className="hr-account-import-table-wrap">
                  <table className="hr-account-import-table">
                    <thead><tr><th>행 번호</th><th>부서</th><th>이름</th><th>다우오피스</th><th>ERP</th><th>SCM</th><th>NAS</th><th>상태</th><th>오류 내용</th></tr></thead>
                    <tbody>{excelState.preview.rows.map((row) => (
                      <tr key={row.row_number} className={`is-${row.status}`}>
                        <td>{row.row_number}</td><td>{row.data.department || "-"}</td><td>{row.data.name || "-"}</td><td>{row.data.dowoffice || "-"}</td><td>{row.data.erp || "-"}</td><td>{row.data.scm || "-"}</td><td>{row.data.nas || "-"}</td>
                        <td><span className={`hr-account-import-status is-${row.status}`}>{importStatusLabel(row.status)}</span></td>
                        <td className="hr-account-import-errors">{row.errors.length ? row.errors.join(" ") : "-"}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
                {excelState.result ? (
                  <div className="hr-account-import-result" role="status">
                    <strong>일괄등록 처리가 완료되었습니다.</strong>
                    <span>등록 {excelState.result.created_count}건</span>
                    <span>업데이트 {excelState.result.updated_count}건</span>
                    <span>중복 건너뜀 {excelState.result.skipped_count}건</span>
                    <span>오류 제외 {excelState.result.failed_count}건</span>
                  </div>
                ) : null}
                <div className="hr-account-import-actions">
                  <button type="button" onClick={closeExcelModal} disabled={excelState.saving}>닫기</button>
                  <button
                    type="button"
                    className="hr-account-import-submit"
                    onClick={commitExcelImport}
                    disabled={excelState.saving || (excelState.preview.valid_count === 0 && (excelState.duplicatePolicy === "skip" || excelState.preview.duplicate_count === 0))}
                  >{excelState.saving ? "등록 중..." : "정상 데이터 등록"}</button>
                </div>
              </>
            ) : null}
          </section>
        </div>
      ) : null}
    </section>
  );
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())} ${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}`;
}

function padDatePart(value) {
  return String(value).padStart(2, "0");
}

function matchesExcelFilters(item, filters) {
  const matchesTextValues = FILTERABLE_COLUMNS.every((key) => {
    const selectedValues = filters[key];
    return selectedValues === null || selectedValues.includes(normalizeFilterValue(item[key]));
  });
  if (!matchesTextValues || !filters.created_at) return matchesTextValues;
  const createdDate = toLocalDateKey(item.created_at);
  if (!createdDate) return false;
  const dateFilter = filters.created_at;
  const today = toLocalDateKey(new Date());
  if (dateFilter.mode === "today") return createdDate === today;
  if (dateFilter.mode === "last7") return createdDate >= dateDaysAgoKey(6) && createdDate <= today;
  if (dateFilter.mode === "last30") return createdDate >= dateDaysAgoKey(29) && createdDate <= today;
  if (dateFilter.mode === "custom") return (!dateFilter.start || createdDate >= dateFilter.start) && (!dateFilter.end || createdDate <= dateFilter.end);
  return true;
}

function toLocalDateKey(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`;
}

function hasInlineChanges(item, form) {
  return Object.keys(EMPTY_FORM).some((key) => String(item[key] || "") !== String(form[key] || ""));
}

function normalizeFilterValue(value) {
  return String(value ?? "").trim();
}

function filterValueLabel(value) {
  return value === "" ? "(빈 값)" : value;
}

function compareFilterValues(left, right) {
  return filterValueLabel(left).localeCompare(filterValueLabel(right), "ko", { numeric: true, sensitivity: "base" });
}

function compareHrItems(left, right, sortState) {
  if (!sortState.key || !sortState.direction) return 0;
  let comparison;
  if (sortState.key === "created_at") {
    comparison = new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
    if (!Number.isFinite(comparison)) comparison = 0;
  } else {
    comparison = normalizeFilterValue(left[sortState.key]).localeCompare(normalizeFilterValue(right[sortState.key]), "ko", { numeric: true, sensitivity: "base" });
  }
  return sortState.direction === "desc" ? -comparison : comparison;
}

function dateDaysAgoKey(days) {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() - days);
  return toLocalDateKey(date);
}

function loadHrTableView() {
  const fallback = { filters: EMPTY_EXCEL_FILTERS, sort: { key: null, direction: null } };
  try {
    const stored = JSON.parse(window.sessionStorage.getItem(HR_TABLE_VIEW_STORAGE_KEY) || "null");
    if (!stored || typeof stored !== "object") return fallback;
    const filters = { ...EMPTY_EXCEL_FILTERS };
    FILTERABLE_COLUMNS.forEach((key) => {
      filters[key] = Array.isArray(stored.filters?.[key]) ? stored.filters[key].map(normalizeFilterValue) : null;
    });
    const dateFilter = stored.filters?.created_at;
    if (dateFilter && ["today", "last7", "last30", "custom"].includes(dateFilter.mode)) {
      filters.created_at = { mode: dateFilter.mode, start: dateFilter.start || "", end: dateFilter.end || "" };
    }
    const sortableKeys = [...FILTERABLE_COLUMNS, "created_at"];
    const sort = sortableKeys.includes(stored.sort?.key) && ["asc", "desc"].includes(stored.sort?.direction)
      ? { key: stored.sort.key, direction: stored.sort.direction }
      : fallback.sort;
    return { filters, sort };
  } catch {
    return fallback;
  }
}

function formatQuickError(error) {
  if (error?.status === 409) return "이미 등록된 계정 정보입니다.";
  if (error?.status >= 500) return "서버 오류로 등록하지 못했습니다. 잠시 후 다시 시도해주세요.";
  return formatHrApiError(error, "계정 등록에 실패했습니다.");
}

function formatHrApiError(error, fallbackMessage) {
  if (error?.status === 404) return `${fallbackMessage} 백엔드 배포 상태를 확인해주세요.`;
  if (error?.status === 403) return "이 작업을 수행할 권한이 없습니다.";
  if (error?.status >= 500) return `${fallbackMessage} 잠시 후 다시 시도해주세요.`;
  return error?.message && error.message !== "Not Found" ? error.message : fallbackMessage;
}

function formatExcelError(error, fallbackMessage) {
  if (error?.status === 413) return "엑셀 파일은 최대 5MB까지 업로드할 수 있습니다.";
  return formatHrApiError(error, fallbackMessage);
}

function importStatusLabel(status) {
  return { valid: "정상", duplicate: "중복", error: "오류" }[status] || status;
}

function saveDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
