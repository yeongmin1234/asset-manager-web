import React, { useEffect, useMemo, useState } from "react";
import { analyzeAssetImage } from "../api/client.js";
import SpecImageInput from "./SpecImageInput.jsx";

const INITIAL_FORM = {
  name: "",
  category_id: "",
  location_group: "",
  location_detail: "",
  department_name: "",
  status: "미사용",
  serial_number: "",
  note: "",
};

const LOCATION_OPTIONS = ["본사", "백화점", "파주창고", "기타"];
const SERIAL_PATTERN = /^[A-Za-z0-9]+$/;
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

function QuickAssetForm({
  categories,
  departments,
  isCategoryDisabled,
  onSubmit,
  onOpenDetailedCreate,
}) {
  const safeCategories = Array.isArray(categories) ? categories : [];
  const safeDepartments = Array.isArray(departments) ? departments : [];
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [specImageFile, setSpecImageFile] = useState(null);
  const [specImageResetKey, setSpecImageResetKey] = useState(0);
  const [analysisState, setAnalysisState] = useState({
    status: "idle",
    result: null,
    message: "",
  });

  const canSubmit = useMemo(
    () =>
      !isSubmitting &&
      !isCategoryDisabled &&
      Boolean(form.name.trim()) &&
      Boolean(form.category_id) &&
      Boolean(form.status),
    [form.category_id, form.name, form.status, isCategoryDisabled, isSubmitting],
  );

  useEffect(() => {
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
  }, [form.category_id, form.name, safeCategories]);

  const handleChange = (event) => {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
    setMessage("");
    setError("");
  };

  const handleReset = () => {
    setForm(INITIAL_FORM);
    setSpecImageFile(null);
    setSpecImageResetKey((current) => current + 1);
    setAnalysisState({ status: "idle", result: null, message: "" });
    setMessage("");
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) {
      setError("제품명, 분류, 상태를 확인해주세요.");
      return;
    }

    const serialNumber = form.serial_number.trim();
    if (serialNumber && !SERIAL_PATTERN.test(serialNumber)) {
      setError("시리얼번호는 영문과 숫자만 입력할 수 있습니다.");
      return;
    }

    const matchedDepartment = findDepartmentByName(
      safeDepartments,
      form.department_name,
    );
    const payload = {
      category_id: Number(form.category_id),
      department_id: matchedDepartment ? matchedDepartment.id : null,
      department_name: form.department_name.trim() || null,
      location_group: form.location_group || null,
      location_detail: form.location_detail.trim() || null,
      name: form.name.trim(),
      model_name: null,
      serial_number: serialNumber || null,
      purchase_date: null,
      purchase_price: null,
      user_name: null,
      status: form.status,
      note: form.note.trim() || null,
      spec_image_file: specImageFile,
    };

    setIsSubmitting(true);
    setMessage("");
    setError("");
    try {
      await onSubmit(payload);
      setForm(INITIAL_FORM);
      setSpecImageFile(null);
      setSpecImageResetKey((current) => current + 1);
      setAnalysisState({ status: "idle", result: null, message: "" });
      setMessage("빠른 등록이 완료되었습니다.");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSpecImageChange = async (file) => {
    setSpecImageFile(file);
    setMessage("");
    setError("");
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
      setForm((currentForm) => ({
        ...currentForm,
        name: result?.product_name || currentForm.name,
        serial_number: currentForm.serial_number || result?.serial_number || "",
        note: mergeAnalysisNote(currentForm.note, buildAnalysisNote(result)),
      }));
    } catch (analysisError) {
      setAnalysisState({
        status: "error",
        result: null,
        message: getFriendlyAnalysisError(analysisError),
      });
    }
  };

  return (
    <section className="quick-create" aria-labelledby="quick-create-title">
      <div className="quick-create-heading">
        <div>
          <h3 id="quick-create-title">빠른 등록</h3>
          <p>제품명, 분류, 상태만으로 자산을 등록합니다.</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          onClick={onOpenDetailedCreate}
        >
          상세 등록
        </button>
      </div>

      <form className="quick-create-form" onSubmit={handleSubmit}>
        <label className="field required">
          <span>제품명</span>
          <input
            name="name"
            value={form.name}
            onChange={handleChange}
            placeholder="제품명"
            required
          />
        </label>

        <label className="field required">
          <span>분류</span>
          <select
            name="category_id"
            value={form.category_id}
            onChange={handleChange}
            disabled={isCategoryDisabled}
            required
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
            list="quick-department-options"
          />
          {safeDepartments.length > 0 && (
            <datalist id="quick-department-options">
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
          <span>시리얼번호</span>
          <input
            name="serial_number"
            value={form.serial_number}
            onChange={handleChange}
            placeholder="예: SN2026001"
          />
        </label>

        <label className="field quick-note-field">
          <span>메모</span>
          <input
            name="note"
            value={form.note}
            onChange={handleChange}
            placeholder="간단한 메모를 입력하세요."
          />
        </label>

        <SpecImageInput
          key={specImageResetKey}
          compact
          onChange={handleSpecImageChange}
        />

        <AssetAnalysisResult state={analysisState} />

        <div className="quick-create-actions">
          {message && <span className="inline-success">{message}</span>}
          {error && <span className="inline-alert">{error}</span>}
          <button type="button" className="secondary-button" onClick={handleReset}>
            입력 초기화
          </button>
          <button type="submit" className="primary-action" disabled={!canSubmit}>
            {isSubmitting ? "등록 중..." : "빠른 등록"}
          </button>
        </div>
      </form>
    </section>
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
  if (!noteText) {
    return existingNote;
  }
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

function findDepartmentByName(items, name) {
  const normalizedName = normalizeDepartmentName(name);
  if (!normalizedName || !Array.isArray(items)) {
    return null;
  }

  return (
    items.find((item) => normalizeDepartmentName(item.name) === normalizedName) || null
  );
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

export default QuickAssetForm;
