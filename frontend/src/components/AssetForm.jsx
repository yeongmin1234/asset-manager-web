import React, { useEffect, useMemo, useState } from "react";
import { analyzeAssetImage } from "../api/client.js";
import SpecImageInput from "./SpecImageInput.jsx";

const INITIAL_FORM = {
  category_id: "",
  department_id: "",
  department_name: "",
  location_group: "",
  location_detail: "",
  name: "",
  model_name: "",
  serial_number: "",
  purchase_date: "",
  purchase_price: "",
  user_name: "",
  status: "미사용",
  note: "",
};

const LOCATION_OPTIONS = ["본사", "백화점", "파주창고", "기타"];
const CATEGORY_NAME_SUGGESTIONS = {
  본체: "데스크탑",
  모니터: "모니터",
  노트북: "노트북",
  마우스: "마우스",
  키보드: "키보드",
  파워케이블: "파워케이블",
  태블릿: "태블릿",
};
const ANALYSIS_FAILURE_MESSAGE =
  "이미지에서 시리얼번호를 찾지 못했습니다. 라벨이 선명하게 보이도록 다시 촬영하거나 다시 업로드해 주세요.";

function AssetForm({
  categories,
  departments,
  lookupError = "",
  lookupState,
  isOpen,
  isSubmitting,
  error,
  initialAsset,
  title = "자산 등록",
  eyebrow = "New asset",
  submitLabel = "저장",
  onClose,
  onSubmit,
}) {
  const safeCategories = Array.isArray(categories) ? categories : [];
  const safeDepartments = Array.isArray(departments) ? departments : [];
  const normalizedInitialForm = useMemo(
    () => normalizeAssetToForm(initialAsset, safeDepartments),
    [initialAsset, safeDepartments],
  );
  const [form, setForm] = useState(normalizedInitialForm);
  const [specImageFile, setSpecImageFile] = useState(null);
  const [deleteSpecImage, setDeleteSpecImage] = useState(false);
  const [analysisState, setAnalysisState] = useState({
    status: "idle",
    result: null,
    message: "",
  });
  const lookupStatus = lookupState || {
    isLoading: false,
    categoryError: lookupError,
    departmentError: lookupError,
  };
  const hasLookupError = Boolean(
    lookupStatus.categoryError || lookupStatus.departmentError,
  );
  const isCategoryDisabled =
    lookupStatus.isLoading ||
    Boolean(lookupStatus.categoryError) ||
    safeCategories.length === 0;

  useEffect(() => {
    if (isOpen) {
      setForm(normalizedInitialForm);
      setSpecImageFile(null);
      setDeleteSpecImage(false);
      setAnalysisState({ status: "idle", result: null, message: "" });
    }
  }, [isOpen, normalizedInitialForm]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const selectedCategory = findCategoryById(safeCategories, form.category_id);
    const suggestedName = CATEGORY_NAME_SUGGESTIONS[selectedCategory?.name];
    if (!suggestedName || form.name.trim()) {
      return;
    }

    setForm((currentForm) => {
      if (currentForm.name.trim()) {
        return currentForm;
      }
      return {
        ...currentForm,
        name: suggestedName,
      };
    });
  }, [form.category_id, form.name, isOpen, safeCategories]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (event) => {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const matchedDepartment = findDepartmentByName(
      safeDepartments,
      form.department_name,
    );
    const payload = {
      ...form,
      category_id: form.category_id ? Number(form.category_id) : undefined,
      department_id: matchedDepartment ? matchedDepartment.id : null,
      department_name: form.department_name.trim() || null,
      location_group: form.location_group || null,
      location_detail: form.location_detail.trim() || null,
      purchase_date: form.purchase_date || null,
      purchase_price: form.purchase_price ? Number(form.purchase_price) : null,
      model_name: form.model_name || null,
      serial_number: form.serial_number || null,
      user_name: form.user_name || null,
      note: form.note || null,
      spec_image_file: specImageFile,
      delete_spec_image: deleteSpecImage,
    };

    const isCreated = await onSubmit(payload);
    if (isCreated) {
      setForm(INITIAL_FORM);
      setSpecImageFile(null);
      setDeleteSpecImage(false);
      setAnalysisState({ status: "idle", result: null, message: "" });
    }
  };

  const handleClose = () => {
    setForm(normalizedInitialForm);
    setSpecImageFile(null);
    setDeleteSpecImage(false);
    setAnalysisState({ status: "idle", result: null, message: "" });
    onClose();
  };

  const handleSpecImageChange = async (file, shouldDelete) => {
    setSpecImageFile(file);
    setDeleteSpecImage(shouldDelete);
    if (!file) {
      setAnalysisState({ status: "idle", result: null, message: "" });
      return;
    }

    setAnalysisState({ status: "loading", result: null, message: "이미지 분석 중..." });
    try {
      const result = await analyzeAssetImage(file);
      setAnalysisState({
        status: result?.serial_number ? "done" : "error",
        result,
        message: result?.message || ANALYSIS_FAILURE_MESSAGE,
      });
      applyAnalysisResult(result);
    } catch (analysisError) {
      setAnalysisState({
        status: "error",
        result: null,
        message: getFriendlyAnalysisError(analysisError),
      });
    }
  };

  const applyAnalysisResult = (result) => {
    setForm((currentForm) => {
      const nextForm = { ...currentForm };
      if (result?.product_name) {
        nextForm.name = result.product_name;
      }
      if (result?.serial_number) {
        nextForm.serial_number = nextForm.serial_number || result.serial_number;
      }
      if (result?.model_name) {
        nextForm.model_name = result.model_name;
      }
      const noteText = buildAnalysisNote(result);
      if (noteText) {
        nextForm.note = mergeAnalysisNote(nextForm.note, noteText);
      }
      return nextForm;
    });
  };

  const canSubmit =
    !isSubmitting &&
    !isCategoryDisabled &&
    Boolean(form.name.trim()) &&
    Boolean(form.category_id) &&
    Boolean(form.status);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" aria-labelledby="asset-form-title">
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 id="asset-form-title">{title}</h2>
          </div>
          <button type="button" className="icon-button" onClick={handleClose} aria-label="닫기">
            ×
          </button>
        </div>

        {lookupStatus.isLoading && (
          <div className="inline-info">
            분류/부서 정보를 불러오는 중입니다.
          </div>
        )}

        {hasLookupError && !lookupStatus.isLoading && (
          <div className="inline-alert">
            분류 또는 부서 후보를 불러오지 못했습니다. Backend 또는 DB 상태를 확인하세요.
          </div>
        )}

        {!lookupStatus.isLoading &&
          !lookupStatus.categoryError &&
          safeCategories.length === 0 && (
            <div className="inline-alert">
              등록된 분류가 없습니다. 기본 데이터를 확인해주세요.
            </div>
          )}

        <form className="asset-form" onSubmit={handleSubmit}>
          <label className="field required">
            <span>제품명</span>
            <input name="name" value={form.name} onChange={handleChange} required />
          </label>

          <label className="field required">
            <span>분류</span>
            <select
              name="category_id"
              value={form.category_id}
              onChange={handleChange}
              required
              disabled={isCategoryDisabled}
            >
              <option value="">분류 선택</option>
              {safeCategories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>위치</span>
            <select name="location_group" value={form.location_group} onChange={handleChange}>
              <option value="">위치 선택</option>
              {LOCATION_OPTIONS.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>세부 위치</span>
            <input
              name="location_detail"
              value={form.location_detail}
              onChange={handleChange}
              placeholder="예: 롯데 본점, 본사 전산실, 파주창고 1층"
            />
          </label>

          <label className="field">
            <span>부서(사용자명)</span>
            <input
              name="department_name"
              value={form.department_name}
              onChange={handleChange}
              placeholder="예: 총무팀, 홍길동, 영업팀 김대리"
              list="department-name-options"
            />
            {safeDepartments.length > 0 && (
              <datalist id="department-name-options">
                {safeDepartments.map((department) => (
                  <option key={department.id} value={department.name} />
                ))}
              </datalist>
            )}
          </label>

          <label className="field required">
            <span>상태</span>
            <select name="status" value={form.status} onChange={handleChange} required>
              <option value="미사용">미사용</option>
              <option value="사용중">사용중</option>
              <option value="폐기">폐기</option>
            </select>
          </label>

          <label className="field">
            <span>모델명</span>
            <input name="model_name" value={form.model_name} onChange={handleChange} />
          </label>

          <label className="field">
            <span>시리얼번호</span>
            <input
              name="serial_number"
              value={form.serial_number}
              onChange={handleChange}
              placeholder="예: SN-2026-001"
            />
          </label>

          <label className="field">
            <span>구매일</span>
            <input
              name="purchase_date"
              type="date"
              value={form.purchase_date}
              onChange={handleChange}
            />
          </label>

          <label className="field">
            <span>구매금액</span>
            <input
              name="purchase_price"
              type="number"
              min="0"
              step="0.01"
              value={form.purchase_price}
              onChange={handleChange}
            />
          </label>

          <label className="field">
            <span>사용자명</span>
            <input name="user_name" value={form.user_name} onChange={handleChange} />
          </label>

          <label className="field field-wide">
            <span>메모</span>
            <textarea name="note" value={form.note} onChange={handleChange} rows="3" />
          </label>

          <SpecImageInput
            initialUrl={initialAsset?.spec_image_url || ""}
            onChange={handleSpecImageChange}
          />

          <AssetAnalysisResult state={analysisState} />

          {error && <div className="inline-alert">{error}</div>}

          <div className="form-actions">
            <button type="button" className="secondary-button" onClick={handleClose}>
              취소
            </button>
            <button type="submit" disabled={!canSubmit}>
              {isSubmitting ? "저장 중..." : submitLabel}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function AssetAnalysisResult({ state }) {
  if (!state || state.status === "idle") {
    return null;
  }

  if (state.status === "loading") {
    return <div className="asset-analysis-panel asset-analysis-loading">이미지 분석 중...</div>;
  }

  if (state.status === "error") {
    return (
      <div className="asset-analysis-panel asset-analysis-error">
        {state.message || ANALYSIS_FAILURE_MESSAGE}
      </div>
    );
  }

  const result = state.result || {};
  return (
    <section className="asset-analysis-panel" aria-label="자동 분석 결과">
      <h3>자동 분석 결과</h3>
      <dl className="asset-analysis-grid">
        <AnalysisItem label="제품명" value={result.product_name} />
        <AnalysisItem label="제조사" value={result.manufacturer} />
        <AnalysisItem label="모델명" value={result.model_name} />
        <AnalysisItem label="제품번호(Type)" value={result.product_number} />
        <AnalysisItem label="시리얼번호" value={result.serial_number} />
      </dl>
    </section>
  );
}

function AnalysisItem({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value || "-"}</dd>
    </div>
  );
}

function buildAnalysisNote(result) {
  if (!result?.model_name && !result?.product_number) {
    return "";
  }
  return [
    result.product_name,
    result.model_name ? `Model: ${result.model_name}` : "",
    result.product_number ? `Type: ${result.product_number}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

function mergeAnalysisNote(currentNote, noteText) {
  const existingNote = String(currentNote || "").trim();
  if (!existingNote) {
    return noteText;
  }
  if (existingNote.includes(noteText)) {
    return existingNote;
  }
  return `${existingNote}\n${noteText}`;
}

function getFriendlyAnalysisError(error) {
  if (error?.status === 400 && error.message) {
    return error.message;
  }
  return ANALYSIS_FAILURE_MESSAGE;
}

function normalizeAssetToForm(asset, departments = []) {
  if (!asset) {
    return INITIAL_FORM;
  }

  const departmentName =
    asset.department_name || findDepartmentById(departments, asset.department_id)?.name || "";

  return {
    category_id: asset.category_id ? String(asset.category_id) : "",
    department_id: asset.department_id ? String(asset.department_id) : "",
    department_name: departmentName,
    location_group: asset.location_group || "",
    location_detail: asset.location_detail || "",
    name: asset.name || "",
    model_name: asset.model_name || "",
    serial_number: asset.serial_number || "",
    purchase_date: asset.purchase_date || "",
    purchase_price:
      asset.purchase_price === null || asset.purchase_price === undefined
        ? ""
        : String(asset.purchase_price),
    user_name: asset.user_name || "",
    status: asset.status || "미사용",
    note: asset.note || "",
  };
}

function findDepartmentByName(items, name) {
  const normalizedName = normalizeDepartmentName(name);
  if (!normalizedName || !Array.isArray(items)) {
    return null;
  }

  return (
    items.find((item) => normalizeDepartmentName(item.name) === normalizedName) || null
  );
}

function findDepartmentById(items, id) {
  if (!id || !Array.isArray(items)) {
    return null;
  }
  return items.find((item) => item.id === id) || null;
}

function findCategoryById(items, id) {
  if (!id || !Array.isArray(items)) {
    return null;
  }
  return items.find((item) => String(item.id) === String(id)) || null;
}

function normalizeDepartmentName(value) {
  return String(value || "")
    .trim()
    .replace(/팀$/, "")
    .toLocaleLowerCase("ko-KR");
}

export default AssetForm;
