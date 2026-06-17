import React, { useEffect, useMemo, useState } from "react";

const INITIAL_FORM = {
  company_name: "",
  vehicle_number: "",
  vehicle_name: "",
  driver_name: "",
  ownership_type: "회사",
  insurance_company: "",
  insurance_type: "",
  insurance_start_date: "",
  insurance_end_date: "",
  lease_company: "",
  lease_start_date: "",
  lease_end_date: "",
  monthly_lease_amount: "",
  lease_payment_day: "",
  tax_note: "",
};

function VehicleQuickForm({ editingItem, onCancelEdit, onSubmit, showHeading = true }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [activeTab, setActiveTab] = useState("basic");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const isEditMode = Boolean(editingItem);

  useEffect(() => {
    if (!editingItem) {
      setForm(INITIAL_FORM);
      setActiveTab("basic");
      setMessage("");
      setError("");
      return;
    }

    setForm({
      company_name: editingItem.company_name || "",
      vehicle_number: editingItem.vehicle_number || "",
      vehicle_name: editingItem.vehicle_name || "",
      driver_name: editingItem.driver_name || "",
      ownership_type: editingItem.ownership_type || "회사",
      insurance_company: editingItem.insurance_company || "",
      insurance_type: editingItem.insurance_type || "",
      insurance_start_date: editingItem.insurance_start_date || "",
      insurance_end_date: editingItem.insurance_end_date || "",
      lease_company: editingItem.lease_company || "",
      lease_start_date: editingItem.lease_start_date || "",
      lease_end_date: editingItem.lease_end_date || "",
      monthly_lease_amount: String(editingItem.monthly_lease_amount ?? ""),
      lease_payment_day: editingItem.lease_payment_day || "",
      tax_note: editingItem.tax_note || "",
    });
    setActiveTab("basic");
    setMessage("");
    setError("");
  }, [editingItem]);

  const canSubmit = useMemo(
    () =>
      !isSubmitting
      && Boolean(form.vehicle_number.trim())
      && Boolean(form.vehicle_name.trim()),
    [form.vehicle_name, form.vehicle_number, isSubmitting],
  );

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setMessage("");
    setError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) {
      setError("차량번호와 차명을 입력해주세요.");
      return;
    }

    const payload = {
      company_name: textOrNull(form.company_name),
      vehicle_number: form.vehicle_number.trim(),
      vehicle_name: form.vehicle_name.trim(),
      driver_name: textOrNull(form.driver_name),
      ownership_type: form.ownership_type,
      insurance_company: textOrNull(form.insurance_company),
      insurance_type: textOrNull(form.insurance_type),
      insurance_start_date: form.insurance_start_date || null,
      insurance_end_date: form.insurance_end_date || null,
      lease_company: textOrNull(form.lease_company),
      lease_start_date: form.lease_start_date || null,
      lease_end_date: form.lease_end_date || null,
      monthly_lease_amount: form.monthly_lease_amount === "" ? null : Number(form.monthly_lease_amount),
      lease_payment_day: textOrNull(form.lease_payment_day),
      tax_note: textOrNull(form.tax_note),
    };

    setIsSubmitting(true);
    setError("");
    setMessage("");
    try {
      await onSubmit(payload);
      setForm(INITIAL_FORM);
      setMessage(isEditMode ? "차량 수정이 완료되었습니다." : "차량 등록이 완료되었습니다.");
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section
      className="quick-create vehicle-quick-form"
      aria-label={showHeading ? undefined : isEditMode ? "차량 수정" : "빠른 등록"}
      aria-labelledby={showHeading ? "vehicle-form-title" : undefined}
    >
      {showHeading && (
        <div className="quick-create-heading">
          <div>
            <h3 id="vehicle-form-title">{isEditMode ? "차량 수정" : "빠른 등록"}</h3>
            <p>{isEditMode ? "선택한 차량 정보를 수정합니다." : "법인차량과 보험/리스 정보를 등록합니다."}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="vehicle-form-tabs" aria-label="차량 등록 정보 탭">
          <button
            type="button"
            className={activeTab === "basic" ? "vehicle-form-tab active" : "vehicle-form-tab"}
            onClick={() => setActiveTab("basic")}
          >
            기본/보험 정보
          </button>
          <button
            type="button"
            className={activeTab === "lease" ? "vehicle-form-tab active" : "vehicle-form-tab"}
            onClick={() => setActiveTab("lease")}
          >
            리스 정보
          </button>
        </div>

        {activeTab === "basic" && (
          <div className="vehicle-create-form">
            <Field name="company_name" label="사업자" value={form.company_name} onChange={handleChange} />
            <Field name="vehicle_number" label="차량번호" value={form.vehicle_number} onChange={handleChange} required />
            <Field name="vehicle_name" label="차명" value={form.vehicle_name} onChange={handleChange} required />
            <Field name="driver_name" label="사용자" value={form.driver_name} onChange={handleChange} />
            <label className="field">
              <span>소유권</span>
              <select name="ownership_type" value={form.ownership_type} onChange={handleChange}>
                <option value="회사">회사</option>
                <option value="리스">리스</option>
              </select>
            </label>
            <Field name="insurance_company" label="보험사" value={form.insurance_company} onChange={handleChange} />
            <Field name="insurance_start_date" label="보험 시작일" type="date" value={form.insurance_start_date} onChange={handleChange} />
            <Field name="insurance_end_date" label="보험 종료일" type="date" value={form.insurance_end_date} onChange={handleChange} />
          </div>
        )}

        {activeTab === "lease" && (
          <div className="vehicle-create-form vehicle-lease-form">
            <Field name="lease_company" label="리스사" value={form.lease_company} onChange={handleChange} />
            <Field name="lease_start_date" label="리스 시작일" type="date" value={form.lease_start_date} onChange={handleChange} />
            <Field name="lease_end_date" label="리스 종료일" type="date" value={form.lease_end_date} onChange={handleChange} />
            <Field name="monthly_lease_amount" label="월 리스금액" type="number" min="0" value={form.monthly_lease_amount} onChange={handleChange} />
            <Field name="lease_payment_day" label="리스 납부일" value={form.lease_payment_day} onChange={handleChange} />
            <label className="field vehicle-tax-note-field">
              <span>자동차세 및 기타</span>
              <textarea name="tax_note" rows="2" value={form.tax_note} onChange={handleChange} />
            </label>
          </div>
        )}

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

function Field({ label, required = false, ...props }) {
  return (
    <label className={required ? "field required" : "field"}>
      <span>{label}</span>
      <input required={required} {...props} />
    </label>
  );
}

function textOrNull(value) {
  const trimmedValue = value.trim();
  return trimmedValue || null;
}

export default VehicleQuickForm;
