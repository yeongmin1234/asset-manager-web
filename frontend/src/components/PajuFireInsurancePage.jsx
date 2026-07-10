import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createPajuFireInsuranceContract,
  deletePajuFireInsuranceContract,
  getPajuFireInsuranceContracts,
  getPajuFireInsuranceSummary,
  updatePajuFireInsuranceContract,
} from "../api/client.js";
import {
  SORT_VALUES,
  VEHICLE_SORT_OPTIONS,
  SortSelect,
  sortItems,
} from "../utils/sortOptions.jsx";
import AttachmentPanel from "./AttachmentPanel.jsx";

const INITIAL_FORM = {
  location_group: "송촌동",
  warehouse_name: "",
  insurer_name: "",
  contractor: "",
  building_coverage: "",
  inventory_coverage: "",
  facility_coverage: "",
  liability_coverage: "",
  monthly_premium: "",
  annual_premium: "",
  contract_start_date: "",
  contract_end_date: "",
  note: "",
};

const INITIAL_FILTERS = {
  location_group: "",
  contractor: "",
  keyword: "",
};

const INITIAL_SUMMARY = {
  total: 0,
  songchon: 0,
  sinchon: 0,
  monthly_premium_total: 0,
  annual_premium_total: 0,
  ending_soon: 0,
};

const LOCATION_OPTIONS = ["송촌동", "신촌동", "기타"];
const CONTRACTOR_OPTIONS = ["한국리모텍", "더리모"];
const LOCATION_TABS = [
  { label: "전체", value: "" },
  { label: "송촌동", value: "송촌동" },
  { label: "신촌동", value: "신촌동" },
  { label: "기타", value: "기타" },
];
const PAJU_FIRE_COLUMN_WIDTH_STORAGE_KEY = "assetManager.pajuFireInsuranceTable.columnWidths";
const PAJU_FIRE_COLUMNS = [
  { key: "insurer", label: "보험사/담보", initialWidth: 140, minWidth: 100 },
  { key: "contractor", label: "계약자", initialWidth: 120, minWidth: 90 },
  { key: "buildingCoverage", label: "건물", initialWidth: 100, minWidth: 80 },
  { key: "inventoryCoverage", label: "재고자산", initialWidth: 110, minWidth: 90 },
  { key: "facilityCoverage", label: "시설/집기", initialWidth: 110, minWidth: 90 },
  { key: "liabilityCoverage", label: "화재배상", initialWidth: 130, minWidth: 100 },
  { key: "monthlyPremium", label: "월보험료", initialWidth: 120, minWidth: 100 },
  { key: "annualPremium", label: "연보험료", initialWidth: 130, minWidth: 110 },
  { key: "contractStartDate", label: "계약시작일", initialWidth: 120, minWidth: 100 },
  { key: "note", label: "비고", initialWidth: 220, minWidth: 140 },
  { key: "actions", label: "관리", initialWidth: 120, minWidth: 110 },
];

function PajuFireInsurancePage({ currentUser }) {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [listState, setListState] = useState({ isLoading: false, error: "" });
  const [summaryState, setSummaryState] = useState({ isLoading: false, error: "" });
  const [submitState, setSubmitState] = useState({ isSubmitting: false, message: "", error: "" });
  const [sortValue, setSortValue] = useState(SORT_VALUES.latest);

  const displayedItems = useMemo(
    () => sortItems(filterContracts(items, filters), sortValue, {
      created: ["created_at", "contract_start_date"],
      updated: ["updated_at", "created_at"],
      name: ["warehouse_name", "insurer_name", "contractor"],
      expiry: ["contract_end_date"],
    }),
    [filters, items, sortValue],
  );

  const loadItems = useCallback(async () => {
    setListState({ isLoading: true, error: "" });
    try {
      setItems(await getPajuFireInsuranceContracts());
      setListState({ isLoading: false, error: "" });
    } catch (error) {
      setItems([]);
      setListState({ isLoading: false, error: error.message });
    }
  }, []);

  const loadSummary = useCallback(async () => {
    setSummaryState({ isLoading: true, error: "" });
    try {
      setSummary({ ...INITIAL_SUMMARY, ...(await getPajuFireInsuranceSummary()) });
      setSummaryState({ isLoading: false, error: "" });
    } catch (error) {
      setSummary(INITIAL_SUMMARY);
      setSummaryState({ isLoading: false, error: error.message });
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    if (!editingItem) {
      setForm(INITIAL_FORM);
      setSubmitState({ isSubmitting: false, message: "", error: "" });
      return;
    }

    setForm({
      location_group: editingItem.location_group || "송촌동",
      warehouse_name: editingItem.warehouse_name || "",
      insurer_name: editingItem.insurer_name || "",
      contractor: editingItem.contractor || "",
      building_coverage: editingItem.building_coverage || "",
      inventory_coverage: editingItem.inventory_coverage || "",
      facility_coverage: editingItem.facility_coverage || "",
      liability_coverage: editingItem.liability_coverage || "",
      monthly_premium: String(editingItem.monthly_premium ?? ""),
      annual_premium: String(editingItem.annual_premium ?? ""),
      contract_start_date: editingItem.contract_start_date || "",
      contract_end_date: editingItem.contract_end_date || "",
      note: editingItem.note || "",
    });
    setSubmitState({ isSubmitting: false, message: "", error: "" });
  }, [editingItem]);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setSubmitState((currentState) => ({ ...currentState, message: "", error: "" }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const payload = buildPayload(form);
    setSubmitState({ isSubmitting: true, message: "", error: "" });
    try {
      if (editingItem) {
        await updatePajuFireInsuranceContract(editingItem.id, payload);
        setEditingItem(null);
        setSubmitState({ isSubmitting: false, message: "계약 수정이 완료되었습니다.", error: "" });
      } else {
        await createPajuFireInsuranceContract(payload);
        setForm(INITIAL_FORM);
        setSubmitState({ isSubmitting: false, message: "계약 등록이 완료되었습니다.", error: "" });
      }
      await Promise.all([loadItems(), loadSummary()]);
    } catch (error) {
      setSubmitState({ isSubmitting: false, message: "", error: error.message });
    }
  };

  const handleDelete = async (item) => {
    const targetName = [item.location_group, item.insurer_name, item.contractor].filter(Boolean).join(" / ");
    const confirmed = window.confirm(`${targetName || "선택한 계약"} 항목을 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    await deletePajuFireInsuranceContract(item.id);
    if (editingItem?.id === item.id) {
      setEditingItem(null);
    }
    await Promise.all([loadItems(), loadSummary()]);
  };

  return (
    <div className="paju-fire-page">
      <div className="portal-screen-heading paju-fire-heading">
        <div>
          <h2>파주화재보험</h2>
          <p>파주 창고/건물 화재보험 계약 정보를 관리합니다.</p>
        </div>
      </div>

      <PajuFireInsuranceStats
        summary={summary}
        isLoading={summaryState.isLoading}
        error={summaryState.error}
      />

      <section className="quick-create paju-fire-form-panel">
        <div className="quick-create-heading">
          <div>
            <h3>{editingItem ? "계약 수정" : "빠른 등록"}</h3>
            <p>보장금액은 입력 표현 그대로 저장하고, 보험료만 합계로 계산합니다.</p>
          </div>
        </div>
        <form className="paju-fire-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>구역</span>
            <select name="location_group" value={form.location_group} onChange={handleChange}>
              {LOCATION_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <Field name="warehouse_name" label="창고" value={form.warehouse_name} onChange={handleChange} />
          <Field name="insurer_name" label="보험사/담보" value={form.insurer_name} onChange={handleChange} />
          <Field name="contractor" label="계약자" value={form.contractor} onChange={handleChange} />
          <Field name="building_coverage" label="건물 보장금액" value={form.building_coverage} onChange={handleChange} />
          <Field name="inventory_coverage" label="재고자산 보장금액" value={form.inventory_coverage} onChange={handleChange} />
          <Field name="facility_coverage" label="시설/집기 보장금액" value={form.facility_coverage} onChange={handleChange} />
          <Field name="liability_coverage" label="화재배상 보장금액" value={form.liability_coverage} onChange={handleChange} />
          <Field name="monthly_premium" label="월보험료" type="number" min="0" value={form.monthly_premium} onChange={handleChange} />
          <Field name="annual_premium" label="연보험료" type="number" min="0" value={form.annual_premium} onChange={handleChange} />
          <Field name="contract_start_date" label="계약시작일" type="date" value={form.contract_start_date} onChange={handleChange} />
          <Field name="contract_end_date" label="계약종료일" type="date" value={form.contract_end_date} onChange={handleChange} />
          <label className="field paju-fire-note-field">
            <span>비고</span>
            <textarea name="note" rows="2" value={form.note} onChange={handleChange} />
          </label>
          <div className="quick-create-actions">
            {submitState.message && <span className="inline-success">{submitState.message}</span>}
            {submitState.error && <span className="inline-alert">{submitState.error}</span>}
            {editingItem && (
              <button type="button" className="secondary-button" onClick={() => setEditingItem(null)}>
                수정 취소
              </button>
            )}
            <button type="submit" className="primary-action" disabled={submitState.isSubmitting}>
              {submitState.isSubmitting ? "저장 중..." : editingItem ? "수정 저장" : "저장"}
            </button>
          </div>
        </form>
      </section>

      <PajuFireInsuranceList
        items={displayedItems}
        currentUser={currentUser}
        isLoading={listState.isLoading}
        error={listState.error}
        filters={filters}
        editingItemId={editingItem?.id || null}
        onDelete={handleDelete}
        onEdit={setEditingItem}
        onFilterChange={setFilters}
        onSortChange={setSortValue}
        sortValue={sortValue}
      />
    </div>
  );
}

function PajuFireInsuranceStats({ summary, isLoading, error }) {
  const cards = [
    { label: "전체 계약", value: Number(summary.total || 0).toLocaleString("ko-KR") },
    { label: "송촌동", value: Number(summary.songchon || 0).toLocaleString("ko-KR") },
    { label: "신촌동", value: Number(summary.sinchon || 0).toLocaleString("ko-KR") },
    { label: "월보험료 합계", value: formatCurrency(summary.monthly_premium_total) },
    { label: "연보험료 합계", value: formatCurrency(summary.annual_premium_total) },
    { label: "만기 임박", value: Number(summary.ending_soon || 0).toLocaleString("ko-KR") },
  ];
  return (
    <section className="paju-fire-stats">
      {cards.map((card) => (
        <article className="paju-fire-stat-card" key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
      {isLoading && <span className="status-pill">집계 중</span>}
      {error && <span className="lookup-warning">{error}</span>}
    </section>
  );
}

function PajuFireInsuranceList({
  items,
  currentUser,
  isLoading,
  error,
  filters,
  editingItemId,
  onDelete,
  onEdit,
  onFilterChange,
  onSortChange,
  sortValue,
}) {
  const safeItems = Array.isArray(items) ? items : [];
  const subtotal = useMemo(() => getContractSubtotal(safeItems), [safeItems]);
  const [columnWidths, setColumnWidths] = useState(() =>
    getInitialColumnWidths(PAJU_FIRE_COLUMNS, PAJU_FIRE_COLUMN_WIDTH_STORAGE_KEY),
  );
  const [selectedNoteContract, setSelectedNoteContract] = useState(null);
  const [noteCopyMessage, setNoteCopyMessage] = useState("");
  const resizeStateRef = useRef(null);
  const noteCopyTimerRef = useRef(null);

  const tableWidth = useMemo(
    () => PAJU_FIRE_COLUMNS.reduce((total, column) => total + columnWidths[column.key], 0),
    [columnWidths],
  );

  const handleColumnResizeStart = (event, column) => {
    event.preventDefault();
    event.stopPropagation();
    resizeStateRef.current = {
      key: column.key,
      minWidth: column.minWidth,
      startX: event.clientX,
      startWidth: columnWidths[column.key],
    };
    document.body.classList.add("paju-fire-column-resizing");

    const handleMouseMove = (moveEvent) => {
      const resizeState = resizeStateRef.current;
      if (!resizeState) {
        return;
      }
      const nextWidth = Math.max(
        resizeState.minWidth,
        resizeState.startWidth + moveEvent.clientX - resizeState.startX,
      );
      setColumnWidths((currentWidths) => {
        const nextWidths = { ...currentWidths, [resizeState.key]: nextWidth };
        saveColumnWidths(PAJU_FIRE_COLUMN_WIDTH_STORAGE_KEY, nextWidths);
        return nextWidths;
      });
    };

    const handleMouseUp = () => {
      resizeStateRef.current = null;
      document.body.classList.remove("paju-fire-column-resizing");
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
  };

  useEffect(
    () => () => {
      window.clearTimeout(noteCopyTimerRef.current);
    },
    [],
  );

  useEffect(
    () => {
      setNoteCopyMessage("");
    },
    [selectedNoteContract],
  );

  const handleNoteCopy = async () => {
    if (!selectedNoteContract?.note) {
      return;
    }

    try {
      await navigator.clipboard.writeText(selectedNoteContract.note);
      setNoteCopyMessage("복사되었습니다.");
    } catch {
      setNoteCopyMessage("복사하지 못했습니다.");
    }

    window.clearTimeout(noteCopyTimerRef.current);
    noteCopyTimerRef.current = window.setTimeout(() => {
      setNoteCopyMessage("");
    }, 1800);
  };

  return (
    <section className="content-panel paju-fire-list-panel">
      <div className="section-heading">
        <div>
          <h2>계약 목록</h2>
          <p>구역, 계약자, 검색어 기준으로 계약 정보를 확인합니다.</p>
        </div>
      </div>

      <div className="paju-fire-list-controls">
        <div className="paju-fire-location-tabs" aria-label="파주화재보험 구역 필터">
          {LOCATION_TABS.map((tab) => (
            <button
              type="button"
              key={tab.label}
              className={filters.location_group === tab.value ? "paju-fire-location-tab active" : "paju-fire-location-tab"}
              onClick={() => onFilterChange({ ...filters, location_group: tab.value })}
            >
              <strong>{tab.label}</strong>
              <span>{getLocationTabCount(items, tab.value)}</span>
            </button>
          ))}
        </div>
        <label className="field">
          <span>계약자</span>
          <select
            value={filters.contractor}
            onChange={(event) => onFilterChange({ ...filters, contractor: event.target.value })}
          >
            <option value="">전체</option>
            {CONTRACTOR_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label className="field paju-fire-search-field">
          <span>검색</span>
          <input
            value={filters.keyword}
            onChange={(event) => onFilterChange({ ...filters, keyword: event.target.value })}
            placeholder="창고, 보험사, 계약자, 비고"
          />
        </label>
        <SortSelect
          value={sortValue}
          options={VEHICLE_SORT_OPTIONS}
          onChange={onSortChange}
        />
      </div>

      {isLoading ? (
        <div className="state-panel">파주화재보험 계약을 불러오는 중입니다.</div>
      ) : error ? (
        <div className="state-panel state-error">
          <strong>계약 목록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      ) : (
        <div className="asset-table-wrap">
          <table className="asset-table paju-fire-table paju-fire-resizable-table" style={{ minWidth: `${tableWidth}px` }}>
            <colgroup>
              {PAJU_FIRE_COLUMNS.map((column) => (
                <col key={column.key} style={{ width: `${columnWidths[column.key]}px` }} />
              ))}
            </colgroup>
            <thead>
              <tr>
                {PAJU_FIRE_COLUMNS.map((column) => (
                  <th key={column.key} className={column.key === "actions" ? "paju-fire-actions-cell" : undefined}>
                    <span className="resizable-table-heading">{column.label}</span>
                    <span
                      aria-hidden="true"
                      className="table-column-resize-handle"
                      onMouseDown={(event) => handleColumnResizeStart(event, column)}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {safeItems.length === 0 ? (
                <tr>
                  <td colSpan="11">
                    <div className="state-panel asset-table-empty-state">
                      <strong>등록된 계약이 없습니다.</strong>
                      <span>빠른 등록 폼으로 파주화재보험 계약을 추가해주세요.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                <>
                  {safeItems.map((item) => (
                    <tr key={item.id} className={editingItemId === item.id ? "editing" : undefined}>
                      <td>{formatText(item.insurer_name)}</td>
                      <td>{formatText(item.contractor)}</td>
                      <td>{formatText(item.building_coverage)}</td>
                      <td>{formatText(item.inventory_coverage)}</td>
                      <td>{formatText(item.facility_coverage)}</td>
                      <td>{formatText(item.liability_coverage)}</td>
                      <td>{formatCurrency(item.monthly_premium)}</td>
                      <td>{formatCurrency(item.annual_premium)}</td>
                      <td>{formatDate(item.contract_start_date)}</td>
                      <td className="paju-fire-note-cell" title={formatText(item.note)}>
                        {hasText(item.note) ? (
                          <button
                            type="button"
                            className="paju-note-text"
                            onClick={() => setSelectedNoteContract(item)}
                          >
                            {formatText(item.note)}
                          </button>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>
                        <div className="software-row-actions paju-fire-actions">
                          <button type="button" className="secondary-button software-action-button" onClick={() => onEdit(item)}>
                            수정
                          </button>
                          <button type="button" className="secondary-button software-action-button" onClick={() => setSelectedNoteContract(item)}>
                            첨부
                          </button>
                          <button type="button" className="danger-button software-action-button" onClick={() => onDelete(item)}>
                            삭제
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  <tr className="paju-fire-subtotal-row">
                    <td>SUB TTL</td>
                    <td />
                    <td>{formatCoverageSubtotal(subtotal.buildingCoverage)}</td>
                    <td>{formatCoverageSubtotal(subtotal.inventoryCoverage)}</td>
                    <td>{formatCoverageSubtotal(subtotal.facilityCoverage)}</td>
                    <td>{formatCoverageSubtotal(subtotal.liabilityCoverage)}</td>
                    <td>{formatCurrency(subtotal.monthlyPremium)}</td>
                    <td>{formatCurrency(subtotal.annualPremium)}</td>
                    <td />
                    <td />
                    <td />
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      )}
      {selectedNoteContract && (
        <div
          className="paju-note-modal-backdrop"
          role="presentation"
          onMouseDown={() => setSelectedNoteContract(null)}
        >
          <section
            className="paju-note-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="paju-note-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="paju-note-modal-heading">
              <div>
                <h3 id="paju-note-modal-title">비고 상세</h3>
                <p>{formatText(selectedNoteContract.insurer_name)}</p>
              </div>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setSelectedNoteContract(null)}
              >
                닫기
              </button>
            </div>
            <dl className="paju-note-modal-meta">
              <div>
                <dt>보험사/담보</dt>
                <dd>{formatText(selectedNoteContract.insurer_name)}</dd>
              </div>
              <div>
                <dt>계약자</dt>
                <dd>{formatText(selectedNoteContract.contractor)}</dd>
              </div>
              <div>
                <dt>계약시작일</dt>
                <dd>{formatDate(selectedNoteContract.contract_start_date)}</dd>
              </div>
            </dl>
            <div className="paju-note-modal-content">
              {formatText(selectedNoteContract.note)}
            </div>
            <AttachmentPanel
              canManage={currentUser?.role === "admin"}
              entityId={selectedNoteContract.id}
              entityType="fire_insurance"
              title="첨부파일"
            />
            <div className="paju-note-modal-actions">
              {noteCopyMessage && <span>{noteCopyMessage}</span>}
              <button type="button" className="secondary-button" onClick={handleNoteCopy}>
                복사
              </button>
              <button type="button" className="primary-button" onClick={() => setSelectedNoteContract(null)}>
                닫기
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function Field({ label, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
  );
}

function buildPayload(form) {
  return {
    location_group: textOrNull(form.location_group),
    warehouse_name: textOrNull(form.warehouse_name),
    insurer_name: textOrNull(form.insurer_name),
    contractor: textOrNull(form.contractor),
    building_coverage: textOrNull(form.building_coverage),
    inventory_coverage: textOrNull(form.inventory_coverage),
    facility_coverage: textOrNull(form.facility_coverage),
    liability_coverage: textOrNull(form.liability_coverage),
    monthly_premium: numberOrNull(form.monthly_premium),
    annual_premium: numberOrNull(form.annual_premium),
    contract_start_date: form.contract_start_date || null,
    contract_end_date: form.contract_end_date || null,
    note: textOrNull(form.note),
  };
}

function filterContracts(items, filters) {
  const keyword = String(filters.keyword || "").trim().toLowerCase();
  return (Array.isArray(items) ? items : []).filter((item) => {
    if (filters.location_group && getContractLocationGroup(item) !== filters.location_group) {
      return false;
    }
    if (filters.contractor && item.contractor !== filters.contractor) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    return [
      item.warehouse_name,
      item.insurer_name,
      item.contractor,
      item.note,
    ].some((value) => String(value || "").toLowerCase().includes(keyword));
  });
}

function getLocationTabCount(items, locationGroup) {
  const safeItems = Array.isArray(items) ? items : [];
  if (!locationGroup) {
    return safeItems.length;
  }
  return safeItems.filter((item) => getContractLocationGroup(item) === locationGroup).length;
}

function getContractLocationGroup(item) {
  const locationText = String(item.location_group || "").trim();
  const warehouseText = String(item.warehouse_name || "").trim();
  if (locationText === "송촌동" || warehouseText === "송촌동") {
    return "송촌동";
  }
  if (locationText === "신촌동" || warehouseText === "신촌동") {
    return "신촌동";
  }
  return "기타";
}

function getContractSubtotal(items) {
  return (Array.isArray(items) ? items : []).reduce(
    (subtotal, item) => ({
      buildingCoverage: subtotal.buildingCoverage + parseSimpleEokCoverage(item.building_coverage),
      inventoryCoverage: subtotal.inventoryCoverage + parseSimpleEokCoverage(item.inventory_coverage),
      facilityCoverage: subtotal.facilityCoverage + parseSimpleEokCoverage(item.facility_coverage),
      liabilityCoverage: subtotal.liabilityCoverage + parseSimpleEokCoverage(item.liability_coverage),
      monthlyPremium: subtotal.monthlyPremium + numberValue(item.monthly_premium),
      annualPremium: subtotal.annualPremium + numberValue(item.annual_premium),
    }),
    {
      buildingCoverage: 0,
      inventoryCoverage: 0,
      facilityCoverage: 0,
      liabilityCoverage: 0,
      monthlyPremium: 0,
      annualPremium: 0,
    },
  );
}

function parseSimpleEokCoverage(value) {
  const text = String(value || "").trim();
  const match = text.match(/^(\d+(?:\.\d+)?)억$/);
  return match ? Number(match[1]) : 0;
}

function formatCoverageSubtotal(value) {
  if (!value) {
    return "-";
  }
  return `${Number(value.toFixed(2)).toLocaleString("ko-KR")}억`;
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function hasText(value) {
  return String(value || "").trim().length > 0;
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return "-";
  }
  return `₩${numberValue.toLocaleString("ko-KR")}`;
}

function numberValue(value) {
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : 0;
}

function formatDate(value) {
  return value || "-";
}

function textOrNull(value) {
  const trimmedValue = String(value || "").trim();
  return trimmedValue || null;
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function getInitialColumnWidths(columns, storageKey) {
  const defaultWidths = columns.reduce(
    (widths, column) => ({ ...widths, [column.key]: column.initialWidth }),
    {},
  );

  if (typeof window === "undefined") {
    return defaultWidths;
  }

  try {
    const savedWidths = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
    return columns.reduce((widths, column) => {
      const savedWidth = Number(savedWidths[column.key]);
      return {
        ...widths,
        [column.key]: Number.isFinite(savedWidth)
          ? Math.max(column.minWidth, savedWidth)
          : column.initialWidth,
      };
    }, {});
  } catch {
    return defaultWidths;
  }
}

function saveColumnWidths(storageKey, widths) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(storageKey, JSON.stringify(widths));
  } catch {
    // Ignore storage failures; resizing still works for the current page state.
  }
}

export default PajuFireInsurancePage;
