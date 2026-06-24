import React, { useEffect, useState } from "react";

const CATEGORY_OPTIONS = ["필수 프로그램", "드라이버", "업무 도구", "보안", "문서", "스크립트", "기타"];
const OS_OPTIONS = ["전체", "Windows", "macOS", "Linux", "NAS", "기타"];
const ALLOWED_EXTENSIONS_TEXT = ".exe, .msi, .zip, .7z, .pdf, .txt, .bat, .ps1";

const EMPTY_FORM = {
  title: "",
  category: "기타",
  os_type: "전체",
  version: "",
  description: "",
  install_guide: "",
  caution_note: "",
  is_required: false,
  install_order: 0,
  file: null,
};

function InstallLibraryForm({
  error = "",
  initialItem = null,
  isOpen = false,
  isSubmitting = false,
  onClose,
  onSubmit,
}) {
  const [form, setForm] = useState(EMPTY_FORM);
  const isEditMode = Boolean(initialItem?.id);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    setForm(
      initialItem
        ? {
            title: initialItem.title || "",
            category: initialItem.category || "기타",
            os_type: initialItem.os_type || "전체",
            version: initialItem.version || "",
            description: initialItem.description || "",
            install_guide: initialItem.install_guide || "",
            caution_note: initialItem.caution_note || "",
            is_required: initialItem.is_required === true,
            install_order: Number(initialItem.install_order || 0),
            file: null,
          }
        : EMPTY_FORM,
    );
  }, [initialItem, isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleChange = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(form);
  };

  return (
    <div className="modal-backdrop install-library-modal-backdrop" role="presentation">
      <section className="install-library-form-modal" role="dialog" aria-modal="true" aria-labelledby="install-library-form-title">
        <div className="install-library-modal-header">
          <div>
            <span className="section-kicker">Install Library Admin</span>
            <h3 id="install-library-form-title">{isEditMode ? "설치자료 수정" : "설치자료 등록"}</h3>
            <p>파일은 서버 업로드 폴더에 저장되고 DB에는 메타데이터만 저장됩니다.</p>
          </div>
          <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
            ×
          </button>
        </div>

        <form className="install-library-form-grid" onSubmit={handleSubmit}>
          <label className="field">
            <span>자료명</span>
            <input value={form.title} required disabled={isSubmitting} onChange={(event) => handleChange("title", event.target.value)} />
          </label>
          <label className="field">
            <span>분류</span>
            <select value={form.category} disabled={isSubmitting} onChange={(event) => handleChange("category", event.target.value)}>
              {CATEGORY_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label className="field">
            <span>OS</span>
            <select value={form.os_type} disabled={isSubmitting} onChange={(event) => handleChange("os_type", event.target.value)}>
              {OS_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label className="field">
            <span>버전</span>
            <input value={form.version} disabled={isSubmitting} onChange={(event) => handleChange("version", event.target.value)} />
          </label>
          <label className="field install-library-form-wide">
            <span>설명</span>
            <textarea value={form.description} disabled={isSubmitting} rows={3} onChange={(event) => handleChange("description", event.target.value)} />
          </label>
          <label className="field install-library-form-wide">
            <span>설치 방법</span>
            <textarea value={form.install_guide} disabled={isSubmitting} rows={4} onChange={(event) => handleChange("install_guide", event.target.value)} />
          </label>
          <label className="field install-library-form-wide">
            <span>주의사항</span>
            <textarea value={form.caution_note} disabled={isSubmitting} rows={3} onChange={(event) => handleChange("caution_note", event.target.value)} />
          </label>
          <label className="field">
            <span>설치 순서</span>
            <input type="number" min="0" value={form.install_order} disabled={isSubmitting} onChange={(event) => handleChange("install_order", event.target.value)} />
          </label>
          <label className="install-library-checkbox">
            <input type="checkbox" checked={form.is_required} disabled={isSubmitting} onChange={(event) => handleChange("is_required", event.target.checked)} />
            <span>필수 설치 항목</span>
          </label>
          <label className="field install-library-form-wide">
            <span>{isEditMode ? "파일 교체" : "파일"}</span>
            <input
              type="file"
              required={!isEditMode}
              disabled={isSubmitting}
              accept=".exe,.msi,.zip,.7z,.pdf,.txt,.bat,.ps1"
              onChange={(event) => handleChange("file", event.target.files?.[0] || null)}
            />
            <small>허용 확장자: {ALLOWED_EXTENSIONS_TEXT}, 최대 500MB</small>
          </label>
          {error && <p className="install-library-form-error install-library-form-wide">{error}</p>}
          <div className="install-library-form-actions install-library-form-wide">
            <button type="button" className="secondary-button" disabled={isSubmitting} onClick={onClose}>
              취소
            </button>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "저장 중" : "저장"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default InstallLibraryForm;
