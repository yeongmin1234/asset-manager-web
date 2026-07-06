import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createVendorContact,
  deleteVendorContact,
  getVendorContacts,
  updateVendorContact,
} from "../api/client.js";

const VENDOR_CONTACT_CATEGORIES = ["전산", "시설", "소모품", "렌탈", "보험", "기타"];
const EMPTY_VENDOR_CONTACT_FORM = {
  category: "전산",
  company_name: "",
  task_name: "",
  manager_name: "",
  phone: "",
  email: "",
  memo: "",
};

function VendorContactsPage() {
  const [contacts, setContacts] = useState([]);
  const [filters, setFilters] = useState({ category: "", keyword: "" });
  const [listState, setListState] = useState({ error: "", isLoading: false });
  const [formState, setFormState] = useState({
    contact: null,
    error: "",
    isOpen: false,
    isSubmitting: false,
  });

  const loadContacts = useCallback(async () => {
    setListState({ error: "", isLoading: true });
    try {
      setContacts(await getVendorContacts(filters));
      setListState({ error: "", isLoading: false });
    } catch (error) {
      setContacts([]);
      setListState({ error: error.message, isLoading: false });
    }
  }, [filters]);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  const contactCountLabel = useMemo(
    () => `${Number(contacts.length || 0).toLocaleString("ko-KR")}건`,
    [contacts.length],
  );

  const openCreateForm = () => {
    setFormState({ contact: null, error: "", isOpen: true, isSubmitting: false });
  };

  const openEditForm = (contact) => {
    setFormState({ contact, error: "", isOpen: true, isSubmitting: false });
  };

  const closeForm = () => {
    setFormState({ contact: null, error: "", isOpen: false, isSubmitting: false });
  };

  const handleSubmit = async (payload) => {
    setFormState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      if (formState.contact) {
        await updateVendorContact(formState.contact.id, payload);
      } else {
        await createVendorContact(payload);
      }
      closeForm();
      await loadContacts();
    } catch (error) {
      setFormState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  const handleDelete = async (contact) => {
    const confirmed = window.confirm(`${contact.company_name || "선택한 업체연락처"}를 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    try {
      await deleteVendorContact(contact.id);
      await loadContacts();
    } catch (error) {
      setListState({ error: error.message, isLoading: false });
    }
  };

  const resetFilters = () => {
    setFilters({ category: "", keyword: "" });
  };

  return (
    <section className="vendor-contacts-page" aria-labelledby="vendor-contacts-title">
      <div className="portal-screen-heading vendor-contacts-heading">
        <div>
          <h2 id="vendor-contacts-title">업체연락처</h2>
          <p>업체별 연락처를 관리합니다.</p>
        </div>
        <button type="button" className="primary-action" onClick={openCreateForm}>
          연락처 등록
        </button>
      </div>

      <section className="content-panel vendor-contact-controls" aria-label="업체연락처 검색 및 필터">
        <label className="field">
          <span>구분</span>
          <select
            value={filters.category}
            onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
          >
            <option value="">전체</option>
            {VENDOR_CONTACT_CATEGORIES.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </label>
        <label className="field vendor-contact-search">
          <span>검색</span>
          <input
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="업체명, 담당업무, 담당자, 연락처, 이메일, 비고"
          />
        </label>
        <button type="button" className="secondary-button" onClick={resetFilters}>
          초기화
        </button>
      </section>

      <section className="content-panel vendor-contact-table-panel">
        <div className="section-heading">
          <div>
            <h3>연락처 목록</h3>
            <p>현재 조건에 맞는 연락처 {contactCountLabel}</p>
          </div>
        </div>

        {listState.isLoading ? (
          <div className="state-panel">업체연락처를 불러오는 중입니다.</div>
        ) : listState.error ? (
          <div className="state-panel state-error">
            <strong>업체연락처를 불러오지 못했습니다.</strong>
            <span className="state-detail">{listState.error}</span>
          </div>
        ) : contacts.length === 0 ? (
          <div className="state-panel">
            <strong>등록된 업체연락처가 없습니다.</strong>
            <span>연락처 등록 버튼으로 첫 연락처를 추가하세요.</span>
          </div>
        ) : (
          <div className="asset-table-wrap vendor-contact-table-wrap">
            <table className="asset-table vendor-contact-table">
              <thead>
                <tr>
                  <th>구분</th>
                  <th>업체명</th>
                  <th>담당업무</th>
                  <th>담당자</th>
                  <th>연락처</th>
                  <th>이메일</th>
                  <th>비고</th>
                  <th>최종수정일</th>
                  <th>관리</th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((contact) => (
                  <tr key={contact.id}>
                    <td><span className="vendor-contact-category">{formatText(contact.category)}</span></td>
                    <td><strong>{formatText(contact.company_name)}</strong></td>
                    <td>{formatText(contact.task_name)}</td>
                    <td>{formatText(contact.manager_name)}</td>
                    <td className="vendor-contact-cell-clip">{formatText(contact.phone)}</td>
                    <td className="vendor-contact-cell-clip">{formatText(contact.email)}</td>
                    <td className="vendor-contact-cell-memo">{formatText(contact.memo)}</td>
                    <td>{formatDateTime(contact.updated_at)}</td>
                    <td>
                      <div className="software-row-actions vendor-contact-actions">
                        <button type="button" className="secondary-button software-action-button" onClick={() => openEditForm(contact)}>
                          수정
                        </button>
                        <button type="button" className="danger-button software-action-button" onClick={() => handleDelete(contact)}>
                          삭제
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <VendorContactFormModal
        contact={formState.contact}
        error={formState.error}
        isOpen={formState.isOpen}
        isSubmitting={formState.isSubmitting}
        onClose={closeForm}
        onSubmit={handleSubmit}
      />
    </section>
  );
}

function VendorContactFormModal({ contact, error, isOpen, isSubmitting, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_VENDOR_CONTACT_FORM);

  useEffect(() => {
    if (!isOpen) {
      setForm(EMPTY_VENDOR_CONTACT_FORM);
      return;
    }
    setForm({
      category: contact?.category || "전산",
      company_name: contact?.company_name || "",
      task_name: contact?.task_name || "",
      manager_name: contact?.manager_name || "",
      phone: contact?.phone || "",
      email: contact?.email || "",
      memo: contact?.memo || "",
    });
  }, [contact, isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.({
      category: form.category,
      company_name: form.company_name,
      task_name: form.task_name,
      manager_name: form.manager_name,
      phone: form.phone,
      email: form.email,
      memo: form.memo,
    });
  };

  return (
    <div className="vendor-contact-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="vendor-contact-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="vendor-contact-form-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="vendor-contact-modal-heading">
            <div>
              <span className="section-kicker">Vendor Contact</span>
              <h3 id="vendor-contact-form-title">{contact ? "업체연락처 수정" : "업체연락처 등록"}</h3>
            </div>
            <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
              x
            </button>
          </div>

          <div className="vendor-contact-form-grid">
            <label className="field">
              <span>구분</span>
              <select name="category" value={form.category} disabled={isSubmitting} onChange={handleChange}>
                {VENDOR_CONTACT_CATEGORIES.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>업체명</span>
              <input
                name="company_name"
                value={form.company_name}
                maxLength={200}
                disabled={isSubmitting}
                required
                onChange={handleChange}
              />
            </label>
            <label className="field">
              <span>담당업무</span>
              <input name="task_name" value={form.task_name} maxLength={200} disabled={isSubmitting} onChange={handleChange} />
            </label>
            <label className="field">
              <span>담당자</span>
              <input name="manager_name" value={form.manager_name} maxLength={100} disabled={isSubmitting} onChange={handleChange} />
            </label>
            <label className="field">
              <span>연락처</span>
              <input name="phone" value={form.phone} maxLength={100} disabled={isSubmitting} onChange={handleChange} />
            </label>
            <label className="field">
              <span>이메일</span>
              <input name="email" value={form.email} maxLength={200} disabled={isSubmitting} onChange={handleChange} />
            </label>
            <label className="field vendor-contact-wide-field">
              <span>비고</span>
              <textarea name="memo" value={form.memo} maxLength={2000} disabled={isSubmitting} rows="4" onChange={handleChange} />
            </label>
          </div>

          {error ? <p className="vendor-contact-form-error">{error}</p> : null}
          <div className="vendor-contact-modal-actions">
            <button type="button" className="secondary-button" disabled={isSubmitting} onClick={onClose}>
              취소
            </button>
            <button type="submit" disabled={isSubmitting || !form.company_name.trim()}>
              {isSubmitting ? "저장 중" : "저장"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const dateValue = new Date(value);
  if (Number.isNaN(dateValue.getTime())) {
    return "-";
  }
  return dateValue.toLocaleString("ko-KR");
}

export default VendorContactsPage;
