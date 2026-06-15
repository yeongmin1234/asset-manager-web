import React, { useEffect, useRef, useState } from "react";

function CategoryCreateModal({ isOpen, error, isSubmitting, onClose, onSubmit }) {
  const [name, setName] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setName("");
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const trimmedName = name.trim();

  const handleSubmit = async (event) => {
    event.preventDefault();
    const didSubmit = await onSubmit(trimmedName);
    if (didSubmit) {
      setName("");
    }
  };

  return (
    <div className="modal-backdrop category-create-backdrop" onMouseDown={onClose}>
      <form
        className="modal category-create-modal"
        onSubmit={handleSubmit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2>분류 추가</h2>
            <p>자산 등록에 사용할 새 분류명을 입력하세요.</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>

        <label className="field">
          <span>분류명</span>
          <input
            ref={inputRef}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="예: 본체, 마우스, 키보드"
          />
        </label>

        {error ? <p className="inline-alert">{error}</p> : null}

        <div className="form-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            취소
          </button>
          <button type="submit" className="primary-action" disabled={!trimmedName || isSubmitting}>
            {isSubmitting ? "추가 중..." : "추가"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default CategoryCreateModal;
