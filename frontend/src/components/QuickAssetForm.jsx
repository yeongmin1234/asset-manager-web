import React, { useMemo, useState } from "react";

const INITIAL_FORM = {
  name: "",
  category_id: "",
  department_name: "",
  status: "미사용",
  serial_number: "",
  note: "",
};

const SERIAL_PATTERN = /^[A-Za-z0-9._-]+$/;

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

  const canSubmit = useMemo(
    () =>
      !isSubmitting &&
      !isCategoryDisabled &&
      Boolean(form.name.trim()) &&
      Boolean(form.category_id) &&
      Boolean(form.status),
    [form.category_id, form.name, form.status, isCategoryDisabled, isSubmitting],
  );

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
      setError("시리얼번호는 영문, 숫자, 마침표, 밑줄, 하이픈만 입력할 수 있습니다.");
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
      name: form.name.trim(),
      model_name: null,
      serial_number: serialNumber || null,
      purchase_date: null,
      purchase_price: null,
      user_name: null,
      status: form.status,
      note: form.note.trim() || null,
    };

    setIsSubmitting(true);
    setMessage("");
    setError("");
    try {
      await onSubmit(payload);
      setForm(INITIAL_FORM);
      setMessage("빠른 등록이 완료되었습니다.");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
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
            placeholder="예: SN-2026-001"
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

function findDepartmentByName(items, name) {
  const normalizedName = normalizeDepartmentName(name);
  if (!normalizedName || !Array.isArray(items)) {
    return null;
  }

  return (
    items.find((item) => normalizeDepartmentName(item.name) === normalizedName) || null
  );
}

function normalizeDepartmentName(value) {
  return String(value || "")
    .trim()
    .replace(/팀$/, "")
    .toLocaleLowerCase("ko-KR");
}

export default QuickAssetForm;
