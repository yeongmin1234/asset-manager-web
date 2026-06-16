import React, { useEffect, useMemo, useState } from "react";

const INITIAL_FORM = {
  name: "",
  owner_name: "",
  license_type: "영구",
  quantity: "1",
  expire_date: "",
  note: "",
};

function SoftwareQuickForm({ editingItem, onCancelEdit, onSubmit }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const canSubmit = useMemo(
    () => !isSubmitting && Boolean(form.name.trim()) && Number(form.quantity || 0) >= 0,
    [form.name, form.quantity, isSubmitting],
  );

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setMessage("");
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) {
      setError("소프트웨어명과 수량을 확인해주세요.");
      return;
    }

    const payload = {
      name: form.name.trim(),
      owner_name: form.owner_name.trim() || null,
      license_type: form.license_type,
      quantity: Number(form.quantity || 0),
      expire_date: form.expire_date || null,
      note: form.note.trim() || null,
    };

    setIsSubmitting(true);
    setError("");
    setMessage("");
    try {
      await onSubmit(payload);
      setForm(INITIAL_FORM);
      setMessage(isEditMode ? "SW 수정이 완료되었습니다." : "SW 등록이 완료되었습니다.");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="quick-create software-quick-form" aria-labelledby="software-form-title">
      <div className="quick-create-heading">
        <div>
          <h3 id="software-form-title">{isEditMode ? "SW 수정" : "빠른 등록"}</h3>
          <p>
            {isEditMode
              ? "선택한 소프트웨어 정보를 수정합니다."
              : "사내 소프트웨어와 라이선스 정보를 등록합니다."}
          </p>
        </div>
      </div>

      <form className="software-create-form" onSubmit={handleSubmit}>
        <label className="field required">
          <span>소프트웨어명</span>
          <input name="name" value={form.name} onChange={handleChange} required />
        </label>
        <label className="field">
          <span>소유</span>
          <input name="owner_name" value={form.owner_name} onChange={handleChange} />
        </label>
        <label className="field">
          <span>종류</span>
          <select name="license_type" value={form.license_type} onChange={handleChange}>
            <option value="영구">영구</option>
            <option value="구독">구독</option>
            <option value="사용중지">사용중지</option>
          </select>
        </label>
        <label className="field">
          <span>수량</span>
          <input
            name="quantity"
            type="number"
            min="0"
            value={form.quantity}
            onChange={handleChange}
          />
        </label>
        <label className="field">
          <span>만료일</span>
          <input
            name="expire_date"
            type="date"
            value={form.expire_date}
            onChange={handleChange}
          />
        </label>
        <label className="field software-note-field">
          <span>기타</span>
          <input name="note" value={form.note} onChange={handleChange} />
        </label>

        <div className="quick-create-actions">
          {message && <span className="inline-success">{message}</span>}
          {error && <span className="inline-alert">{error}</span>}
          {isEditMode && (
            <button type="button" className="secondary-button" onClick={onCancelEdit}>
              수정 취소
            </button>
          )}
          <button type="submit" className="primary-action" disabled={!canSubmit}>
            {isSubmitting ? "저장 중..." : isEditMode ? "수정 저장" : "저장"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default SoftwareQuickForm;
  const isEditMode = Boolean(editingItem);

  useEffect(() => {
    if (!editingItem) {
      setForm(INITIAL_FORM);
      setMessage("");
      setError("");
      return;
    }

    setForm({
      name: editingItem.name || "",
      owner_name: editingItem.owner_name || "",
      license_type: editingItem.license_type || "영구",
      quantity: String(editingItem.quantity ?? 1),
      expire_date: editingItem.expire_date || "",
      note: editingItem.note || "",
    });
    setMessage("");
    setError("");
  }, [editingItem]);
