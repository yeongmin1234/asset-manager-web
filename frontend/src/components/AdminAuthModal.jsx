import React, { useEffect, useRef, useState } from "react";

function AdminAuthModal({
  error = "",
  isOpen,
  isSubmitting = false,
  menuLabel = "보호 메뉴",
  onCancel,
  onPasswordResetRequest,
  onSubmit,
  resetSuccessMessage = "",
}) {
  const [password, setPassword] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setPassword("");
      return;
    }

    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(password);
  };

  return (
    <div className="admin-auth-modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="admin-auth-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-auth-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="admin-auth-modal-heading">
            <div>
              <h3 id="admin-auth-title">관리자 인증</h3>
              <p>{menuLabel} 메뉴는 관리자 확인이 필요합니다.</p>
            </div>
          </div>

          <label className="field admin-auth-password-field">
            <span>비밀번호</span>
            <input
              ref={inputRef}
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              disabled={isSubmitting}
            />
          </label>

          {resetSuccessMessage && <p className="admin-auth-message">{resetSuccessMessage}</p>}
          {error && <p className="admin-auth-error">{error}</p>}

          <div className="admin-auth-modal-actions">
            <button
              type="button"
              className="link-button admin-forgot-password-button"
              onClick={onPasswordResetRequest}
              disabled={isSubmitting}
            >
              비밀번호를 잊으셨나요?
            </button>
            <button type="button" className="secondary-button" onClick={onCancel} disabled={isSubmitting}>
              취소
            </button>
            <button type="submit" disabled={isSubmitting || !password}>
              {isSubmitting ? "확인 중" : "확인"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default AdminAuthModal;
