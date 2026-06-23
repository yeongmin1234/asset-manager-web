import React, { useEffect, useState } from "react";

export const NETWORK_CREDENTIAL_CATEGORIES = [
  "NAS",
  "CCTV",
  "서버",
  "프린터",
  "공유기",
  "VPN",
  "웹관리자",
  "기타",
];

export const NETWORK_CREDENTIAL_IMPORTANCE = ["일반", "중요", "매우중요"];

const EMPTY_FORM = {
  category: "기타",
  service_name: "",
  internal_url: "",
  external_url: "",
  port: "",
  username: "",
  password: "",
  importance: "일반",
  owner: "",
  note: "",
  is_active: true,
};

function NetworkCredentialForm({
  credential = null,
  error = "",
  isOpen,
  isSubmitting = false,
  onClose,
  onSubmit,
}) {
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    if (credential) {
      setForm({
        category: credential.category || "기타",
        service_name: credential.service_name || "",
        internal_url: credential.internal_url || "",
        external_url: credential.external_url || "",
        port: credential.port || "",
        username: credential.username || "",
        password: "",
        importance: credential.importance || "일반",
        owner: credential.owner || "",
        note: credential.note || "",
        is_active: credential.is_active !== false,
      });
      return;
    }

    setForm(EMPTY_FORM);
  }, [credential, isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (field, value) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const payload = {
      ...form,
      service_name: form.service_name.trim(),
      internal_url: form.internal_url.trim() || null,
      external_url: form.external_url.trim() || null,
      port: form.port.trim() || null,
      username: form.username.trim() || null,
      password: form.password || null,
      owner: form.owner.trim() || null,
      note: form.note.trim() || null,
    };
    onSubmit?.(payload);
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="modal network-credential-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="network-credential-form-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="modal-header">
            <div>
              <h2 id="network-credential-form-title">
                {credential ? "접속정보 수정" : "접속정보 등록"}
              </h2>
              <p>비밀번호는 저장 시 암호화되며 목록에는 표시되지 않습니다.</p>
            </div>
            <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
              ×
            </button>
          </div>

          <div className="network-credential-form-grid">
            <label className="field">
              <span>구분</span>
              <select value={form.category} onChange={(event) => handleChange("category", event.target.value)}>
                {NETWORK_CREDENTIAL_CATEGORIES.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>서비스명</span>
              <input
                value={form.service_name}
                maxLength={200}
                required
                onChange={(event) => handleChange("service_name", event.target.value)}
              />
            </label>
            <label className="field">
              <span>내부 주소</span>
              <input
                value={form.internal_url}
                maxLength={500}
                placeholder="IP 또는 내부 URL"
                onChange={(event) => handleChange("internal_url", event.target.value)}
              />
            </label>
            <label className="field">
              <span>외부 주소</span>
              <input
                value={form.external_url}
                maxLength={500}
                placeholder="외부 URL"
                onChange={(event) => handleChange("external_url", event.target.value)}
              />
            </label>
            <label className="field">
              <span>포트</span>
              <input
                value={form.port}
                maxLength={40}
                onChange={(event) => handleChange("port", event.target.value)}
              />
            </label>
            <label className="field">
              <span>계정 ID</span>
              <input
                value={form.username}
                maxLength={200}
                autoComplete="off"
                onChange={(event) => handleChange("username", event.target.value)}
              />
            </label>
            <label className="field">
              <span>비밀번호</span>
              <input
                type="password"
                value={form.password}
                autoComplete="new-password"
                placeholder={credential ? "변경 시에만 입력" : ""}
                onChange={(event) => handleChange("password", event.target.value)}
              />
            </label>
            <label className="field">
              <span>중요도</span>
              <select value={form.importance} onChange={(event) => handleChange("importance", event.target.value)}>
                {NETWORK_CREDENTIAL_IMPORTANCE.map((importance) => (
                  <option key={importance} value={importance}>{importance}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>담당자</span>
              <input
                value={form.owner}
                maxLength={100}
                onChange={(event) => handleChange("owner", event.target.value)}
              />
            </label>
            <label className="field network-credential-note-field">
              <span>비고</span>
              <textarea
                value={form.note}
                rows={3}
                onChange={(event) => handleChange("note", event.target.value)}
              />
            </label>
          </div>

          {error ? <p className="form-error">{error}</p> : null}

          <div className="form-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={isSubmitting}>
              취소
            </button>
            <button
              type="submit"
              disabled={
                isSubmitting ||
                !form.service_name.trim() ||
                (!form.internal_url.trim() && !form.external_url.trim())
              }
            >
              {isSubmitting ? "저장 중" : "저장"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default NetworkCredentialForm;
