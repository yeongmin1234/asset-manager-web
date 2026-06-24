import React, { useEffect, useRef, useState } from "react";

const MIN_PASSWORD_LENGTH = 6;

const INITIAL_FORM = {
  reset_code: "",
  new_password: "",
  confirm_password: "",
};

function AdminPasswordResetModal({
  isOpen,
  isSubmitting = false,
  error = "",
  onClose,
  onSubmit,
}) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [localError, setLocalError] = useState("");
  const resetCodeRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setForm(INITIAL_FORM);
      setLocalError("");
      return;
    }
    window.setTimeout(() => resetCodeRef.current?.focus(), 0);
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setLocalError("");
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (form.new_password.length < MIN_PASSWORD_LENGTH) {
      setLocalError("새 관리자 비밀번호는 6자 이상이어야 합니다.");
      return;
    }
    if (form.new_password !== form.confirm_password) {
      setLocalError("새 비밀번호와 확인값이 일치하지 않습니다.");
      return;
    }
    onSubmit?.(form);
  };

  return (
    <div className="admin-auth-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="admin-auth-modal admin-reset-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-reset-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="admin-auth-modal-heading">
            <div>
              <h3 id="admin-reset-title">관리자 비밀번호 초기화</h3>
              <p>초기화 코드를 확인한 뒤 새 관리자 비밀번호를 설정합니다.</p>
            </div>
          </div>

          <div className="admin-reset-warning">
            <strong>보안 안내</strong>
            <span>초기화 코드는 NAS 서버의 backend/.env에 설정된 코드입니다. 관리자만 사용하세요.</span>
          </div>

          <label className="field admin-auth-password-field">
            <span>초기화 코드</span>
            <input
              ref={resetCodeRef}
              type="password"
              name="reset_code"
              value={form.reset_code}
              autoComplete="off"
              disabled={isSubmitting}
              onChange={handleChange}
            />
          </label>
          <label className="field admin-auth-password-field">
            <span>새 관리자 비밀번호</span>
            <input
              type="password"
              name="new_password"
              value={form.new_password}
              autoComplete="new-password"
              disabled={isSubmitting}
              onChange={handleChange}
            />
          </label>
          <label className="field admin-auth-password-field">
            <span>새 관리자 비밀번호 확인</span>
            <input
              type="password"
              name="confirm_password"
              value={form.confirm_password}
              autoComplete="new-password"
              disabled={isSubmitting}
              onChange={handleChange}
            />
          </label>

          {(localError || error) && <p className="admin-auth-error">{localError || error}</p>}

          <div className="admin-auth-modal-actions">
            <button type="button" className="secondary-button" onClick={onClose} disabled={isSubmitting}>
              취소
            </button>
            <button type="submit" className="caution-button admin-reset-submit" disabled={isSubmitting}>
              {isSubmitting ? "초기화 중" : "비밀번호 초기화"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default AdminPasswordResetModal;
