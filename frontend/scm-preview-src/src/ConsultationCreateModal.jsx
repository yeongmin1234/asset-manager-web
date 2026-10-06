import React, { useEffect, useState } from "react";
import CustomerHistorySection from "./CustomerHistorySection";
import { asHistory, consultationHistory, mockCustomers, salesHistory } from "./consultationMockData";

const emptyForm = { status: "상담접수", customer: "", phone: "", mobile: "", address: "", brand: "", interest: "", detail: "" };

export default function ConsultationCreateModal({ onClose, onCreate }) {
  const [query, setQuery] = useState({ name: "", mobile: "" });
  const [matchedIds, setMatchedIds] = useState([]);
  const [searched, setSearched] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    document.body.classList.add("modal-open");
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("modal-open");
    };
  }, [onClose]);

  const update = (key, value) => {
    if ((key === "phone" || key === "mobile") && !/^[0-9-]*$/.test(value)) return;
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  };

  function searchCustomers(event) {
    event.preventDefault();
    const name = query.name.trim();
    const mobile = query.mobile.replace(/\D/g, "");
    if (!name && !mobile) {
      setSearched(false);
      setMatchedIds([]);
      return;
    }
    setMatchedIds(mockCustomers.filter((customer) => {
      const phones = `${customer.phone}${customer.mobile}`.replace(/\D/g, "");
      return (!name || customer.name.includes(name)) && (!mobile || phones.includes(mobile) || phones.endsWith(mobile));
    }).map((customer) => customer.id));
    setSearched(true);
    setSelectedId("");
  }

  function copyRow(row, includeDetail = false) {
    if (includeDetail && form.detail.trim() && !window.confirm("기존 상담내역을 검색한 상담내역으로 덮어쓰시겠습니까?")) return;
    setSelectedId(row.id);
    setForm((current) => ({
      ...current,
      customer: row.name,
      phone: row.phone,
      mobile: row.mobile,
      address: row.address,
      brand: row.brand,
      interest: row.product,
      detail: includeDetail ? row.detail : current.detail,
    }));
    setErrors({});
  }

  function submit(event) {
    event.preventDefault();
    const next = {};
    if (!form.customer.trim()) next.customer = "고객명을 입력해 주세요.";
    if (!form.mobile.trim()) next.mobile = "핸드폰을 입력해 주세요.";
    if (!form.detail.trim()) next.detail = "상담내역을 입력해 주세요.";
    if (form.phone && !/^[0-9-]+$/.test(form.phone)) next.phone = "숫자와 하이픈만 입력할 수 있습니다.";
    if (!/^[0-9-]+$/.test(form.mobile)) next.mobile = "숫자와 하이픈만 입력할 수 있습니다.";
    setErrors(next);
    if (Object.keys(next).length) return;
    onCreate(form);
  }

  const histories = (rows) => searched ? rows.filter((row) => matchedIds.includes(row.customerId)) : [];
  const field = (key, label, required, placeholder = "") => (
    <label className="consult-create-field">
      <span>{required && <em>*</em>}{label}</span>
      <input value={form[key]} placeholder={placeholder} onChange={(event) => update(key, event.target.value)} />
      {errors[key] && <small>{errors[key]}</small>}
    </label>
  );

  return (
    <div className="consult-create-layer">
      <section className="consult-create-modal" role="dialog" aria-modal="true" aria-labelledby="consult-create-title">
        <header><h2 id="consult-create-title">신규 상담등록</h2><button type="button" onClick={onClose} aria-label="닫기">×</button></header>
        <form className="consult-create-grid" onSubmit={submit} noValidate>
          <div className="consult-create-left">
            <section className="consult-create-section">
              <h3>고객정보 검색</h3>
              <div className="customer-search-fields">
                <label><span>고객명</span><input value={query.name} placeholder="구매자/수취인 동시검색" onChange={(event) => setQuery((current) => ({ ...current, name: event.target.value }))} /></label>
                <label><span>핸드폰</span><input value={query.mobile} placeholder="끝자리 검색 지원" onChange={(event) => setQuery((current) => ({ ...current, mobile: event.target.value }))} /></label>
                <button type="button" onClick={searchCustomers}>검색</button>
              </div>
            </section>
            <section className="consult-create-section consult-create-form">
              <h3>상담내역 입력</h3>
              <fieldset><legend><em>*</em>상담상태</legend>{["상담접수", "회신준비", "상담완료"].map((status) => <label key={status}><input type="radio" name="status" checked={form.status === status} onChange={() => update("status", status)} />{status}</label>)}</fieldset>
              {field("customer", "고객명", true)}
              {field("phone", "전화")}
              {field("mobile", "핸드폰", true)}
              {field("address", "주소")}
              {field("brand", "브랜드")}
              {field("interest", "관심제품")}
              <label className="consult-create-field consult-create-field--textarea"><span><em>*</em>상담내역</span><textarea value={form.detail} placeholder="고객 상담 내역을 기록하십시오" onChange={(event) => update("detail", event.target.value)} />{errors.detail && <small>{errors.detail}</small>}</label>
              <div className="consult-create-submit"><button type="submit">상담등록</button></div>
            </section>
          </div>
          <div className="consult-create-right">
            <CustomerHistorySection title="고객 판매이력 검색 결과" kind="sales" rows={histories(salesHistory)} searched={searched} selectedId={selectedId} onSelect={copyRow} />
            <CustomerHistorySection title="고객 A/S이력 검색 결과" kind="as" rows={histories(asHistory)} searched={searched} selectedId={selectedId} onSelect={copyRow} />
            <CustomerHistorySection title="고객 상담문의이력 검색 결과" kind="consultations" rows={histories(consultationHistory)} searched={searched} selectedId={selectedId} onSelect={(row) => copyRow(row, true)} />
          </div>
        </form>
      </section>
    </div>
  );
}
