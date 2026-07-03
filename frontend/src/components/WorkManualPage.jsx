import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createWorkManual,
  deleteWorkManual,
  getWorkManual,
  getWorkManuals,
  updateWorkManual,
  uploadWorkManualImage,
} from "../api/client.js";

const EMPTY_MANUAL_FORM = {
  category: "일반",
  title: "",
  content: "",
  author: "관리자",
  is_pinned: false,
};

const ADMIN_AUTH_STORAGE_KEY = "assetManager.adminAuth";
const ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;

function WorkManualPage() {
  const [manuals, setManuals] = useState([]);
  const [listState, setListState] = useState({ error: "", isLoading: false });
  const [filters, setFilters] = useState({ keyword: "", category: "" });
  const [selectedManual, setSelectedManual] = useState(null);
  const [detailState, setDetailState] = useState({ error: "", isLoading: false });
  const [formState, setFormState] = useState({
    error: "",
    initialManual: null,
    isOpen: false,
    isSubmitting: false,
  });
  const [deleteState, setDeleteState] = useState({
    error: "",
    isOpen: false,
    isSubmitting: false,
    manual: null,
  });
  const [isAdminAuthorized, setIsAdminAuthorized] = useState(() => hasValidAdminAuth());

  const loadManuals = useCallback(async () => {
    setListState({ error: "", isLoading: true });
    try {
      const data = await getWorkManuals();
      const nextManuals = Array.isArray(data) ? data : [];
      setManuals(nextManuals);
      setSelectedManual((current) => {
        if (!current || nextManuals.some((manual) => manual.id === current.id)) {
          return current;
        }
        return null;
      });
      setListState({ error: "", isLoading: false });
    } catch (error) {
      setManuals([]);
      setSelectedManual(null);
      setListState({ error: error.message, isLoading: false });
    }
  }, []);

  useEffect(() => {
    loadManuals();
  }, [loadManuals]);

  useEffect(() => {
    const refreshAdminState = () => setIsAdminAuthorized(hasValidAdminAuth());
    refreshAdminState();
    window.addEventListener("storage", refreshAdminState);
    window.addEventListener("focus", refreshAdminState);
    return () => {
      window.removeEventListener("storage", refreshAdminState);
      window.removeEventListener("focus", refreshAdminState);
    };
  }, []);

  const categories = useMemo(() => {
    const categorySet = new Set();
    manuals.forEach((manual) => {
      const category = formatText(manual.category);
      if (category !== "-") {
        categorySet.add(category);
      }
    });
    return Array.from(categorySet);
  }, [manuals]);

  const filteredManuals = useMemo(() => {
    const keyword = filters.keyword.trim().toLowerCase();
    return manuals.filter((manual) => {
      const matchesCategory = !filters.category || manual.category === filters.category;
      if (!matchesCategory) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      return [manual.title, manual.content, manual.category]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword));
    });
  }, [filters, manuals]);

  const handleSelectManual = async (manual) => {
    setDetailState({ error: "", isLoading: true });
    try {
      const detail = await getWorkManual(manual.id);
      setSelectedManual(detail);
      setManuals((current) =>
        current.map((item) => (item.id === detail.id ? { ...item, ...detail } : item)),
      );
      setDetailState({ error: "", isLoading: false });
    } catch (error) {
      setDetailState({ error: error.message, isLoading: false });
    }
  };

  const openCreateForm = () => {
    if (!isAdminAuthorized) {
      return;
    }
    setFormState({ error: "", initialManual: null, isOpen: true, isSubmitting: false });
  };

  const openEditForm = (manual) => {
    if (!isAdminAuthorized) {
      return;
    }
    setFormState({ error: "", initialManual: manual, isOpen: true, isSubmitting: false });
  };

  const closeForm = () => {
    setFormState({ error: "", initialManual: null, isOpen: false, isSubmitting: false });
  };

  const handleSubmit = async (payload) => {
    setFormState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      const savedManual = formState.initialManual
        ? await updateWorkManual(formState.initialManual.id, payload)
        : await createWorkManual(payload);
      closeForm();
      await loadManuals();
      if (selectedManual?.id === savedManual.id) {
        setSelectedManual(savedManual);
      }
    } catch (error) {
      setFormState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  const openDelete = (manual) => {
    if (!isAdminAuthorized) {
      return;
    }
    setDeleteState({
      error: "",
      isOpen: true,
      isSubmitting: false,
      manual,
    });
  };

  const closeDelete = () => {
    setDeleteState({
      error: "",
      isOpen: false,
      isSubmitting: false,
      manual: null,
    });
  };

  const handleDelete = async () => {
    if (!deleteState.manual) {
      return;
    }
    setDeleteState((current) => ({ ...current, error: "", isSubmitting: true }));
    try {
      await deleteWorkManual(deleteState.manual.id);
      if (selectedManual?.id === deleteState.manual.id) {
        setSelectedManual(null);
      }
      closeDelete();
      await loadManuals();
    } catch (error) {
      setDeleteState((current) => ({ ...current, error: error.message, isSubmitting: false }));
    }
  };

  return (
    <section className="work-manual-page" aria-labelledby="work-manual-title">
      <div className="portal-screen-heading work-manual-heading">
        <div>
          <span className="section-kicker">Work Manual Board</span>
          <h2 id="work-manual-title">업무설명서</h2>
          <p>자주 사용하는 업무 절차와 내부 기준을 정리합니다.</p>
        </div>
        {isAdminAuthorized ? (
          <button type="button" onClick={openCreateForm}>
            새 글 작성
          </button>
        ) : null}
      </div>

      {!isAdminAuthorized ? (
        <div className="work-manual-admin-notice">관리자 권한이 필요합니다. 목록과 상세 내용은 조회할 수 있습니다.</div>
      ) : null}

      <section className="work-manual-controls" aria-label="업무설명서 검색 및 필터">
        <label>
          <span>검색</span>
          <input
            value={filters.keyword}
            placeholder="제목, 내용, 카테고리"
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
          />
        </label>
        <label>
          <span>카테고리</span>
          <select
            value={filters.category}
            onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
          >
            <option value="">전체</option>
            {categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary-button" onClick={() => setFilters({ keyword: "", category: "" })}>
          초기화
        </button>
        <button type="button" className="secondary-button" onClick={loadManuals}>
          새로고침
        </button>
      </section>

      {detailState.error ? <div className="inline-alert">{detailState.error}</div> : null}

      <div className={selectedManual ? "work-manual-layout work-manual-layout-split" : "work-manual-layout"}>
        <section className="work-manual-board" aria-label="업무설명서 목록">
          <WorkManualTable
            isCompact={Boolean(selectedManual)}
            isLoading={listState.isLoading}
            error={listState.error}
            manuals={filteredManuals}
            selectedManualId={selectedManual?.id}
            onSelectManual={handleSelectManual}
          />
        </section>

        {selectedManual ? (
          <WorkManualPreview
            isLoading={detailState.isLoading}
            manual={selectedManual}
            canManage={isAdminAuthorized}
            onClose={() => setSelectedManual(null)}
            onDelete={openDelete}
            onEdit={openEditForm}
          />
        ) : null}
      </div>

      <WorkManualFormModal
        error={formState.error}
        initialManual={formState.initialManual}
        isOpen={formState.isOpen}
        isSubmitting={formState.isSubmitting}
        onClose={closeForm}
        onSubmit={handleSubmit}
      />
      <WorkManualDeleteModal
        state={deleteState}
        onClose={closeDelete}
        onConfirm={handleDelete}
      />
    </section>
  );
}

function WorkManualTable({
  error,
  isCompact,
  isLoading,
  manuals,
  onSelectManual,
  selectedManualId,
}) {
  if (isLoading) {
    return <div className="work-manual-empty">업무설명서를 불러오는 중입니다.</div>;
  }

  if (error) {
    return <div className="inline-alert">{error}</div>;
  }

  if (manuals.length === 0) {
    return <div className="work-manual-empty">등록된 업무설명서가 없습니다.</div>;
  }

  return (
    <div className={isCompact ? "work-manual-table-wrap work-manual-table-compact" : "work-manual-table-wrap"}>
      <table className="work-manual-table">
        <thead>
          <tr>
            <th>번호</th>
            <th>카테고리</th>
            <th>제목</th>
            {!isCompact ? <th>작성자</th> : null}
            {!isCompact ? <th>작성일</th> : null}
            <th>조회수</th>
          </tr>
        </thead>
        <tbody>
          {manuals.map((manual, index) => {
            const isSelected = selectedManualId === manual.id;
            return (
              <tr
                className={isSelected ? "work-manual-row selected" : "work-manual-row"}
                key={manual.id}
                onClick={() => onSelectManual?.(manual)}
              >
                <td>{manual.is_pinned ? "공지" : manuals.length - index}</td>
                <td>
                  <span className="work-manual-category-badge">{formatText(manual.category)}</span>
                </td>
                <td className="work-manual-title-cell">
                  <button type="button" title={formatText(manual.title)}>
                    {manual.is_pinned ? "[고정] " : ""}{formatText(manual.title)}
                  </button>
                </td>
                {!isCompact ? <td>{formatText(manual.author)}</td> : null}
                {!isCompact ? <td>{formatDate(manual.created_at)}</td> : null}
                <td>{Number(manual.view_count || 0).toLocaleString("ko-KR")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WorkManualPreview({ canManage, isLoading, manual, onClose, onDelete, onEdit }) {
  const [previewImage, setPreviewImage] = useState(null);

  return (
    <aside className="work-manual-preview" aria-label="선택한 업무설명서 미리보기">
      <div className="work-manual-preview-heading">
        <div>
          <span className="work-manual-category-badge">{formatText(manual.category)}</span>
          <h3>{formatText(manual.title)}</h3>
          <div className="work-manual-preview-meta">
            <span>{formatText(manual.author)}</span>
            <span>{formatDateTime(manual.created_at)}</span>
            <span>조회 {Number(manual.view_count || 0).toLocaleString("ko-KR")}</span>
          </div>
        </div>
        <button type="button" className="secondary-button" onClick={onClose}>
          목록으로
        </button>
      </div>
      {isLoading ? (
        <div className="work-manual-empty">본문을 불러오는 중입니다.</div>
      ) : (
        <ManualContent content={manual.content} onImageClick={setPreviewImage} />
      )}
      <div className="work-manual-preview-actions">
        {canManage ? (
          <>
            <button type="button" className="secondary-button" onClick={() => onEdit?.(manual)}>
              수정
            </button>
            <button type="button" className="danger-button" onClick={() => onDelete?.(manual)}>
              삭제
            </button>
          </>
        ) : (
          <span className="work-manual-admin-inline">관리자 권한이 필요합니다.</span>
        )}
        <button type="button" className="secondary-button" onClick={onClose}>
          닫기
        </button>
      </div>
      <WorkManualImageModal image={previewImage} onClose={() => setPreviewImage(null)} />
    </aside>
  );
}

function WorkManualFormModal({ error, initialManual, isOpen, isSubmitting, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_MANUAL_FORM);
  const [uploadState, setUploadState] = useState({ error: "", isDragging: false, isUploading: false });
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setForm(EMPTY_MANUAL_FORM);
      return;
    }
    setForm({
      category: initialManual?.category || "일반",
      title: initialManual?.title || "",
      content: initialManual?.content || "",
      author: initialManual?.author || "관리자",
      is_pinned: Boolean(initialManual?.is_pinned),
    });
  }, [initialManual, isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(form);
  };

  const insertImageMarkdown = (image) => {
    const markdown = `![이미지 설명](${image.url})`;
    const textarea = textareaRef.current;
    setForm((current) => {
      const content = current.content || "";
      if (!textarea) {
        return { ...current, content: content ? `${content}\n\n${markdown}` : markdown };
      }
      const start = textarea.selectionStart || 0;
      const end = textarea.selectionEnd || 0;
      const before = content.slice(0, start);
      const after = content.slice(end);
      const prefix = before && !before.endsWith("\n") ? "\n" : "";
      const suffix = after && !after.startsWith("\n") ? "\n" : "";
      const nextContent = `${before}${prefix}${markdown}${suffix}${after}`;
      window.setTimeout(() => {
        textarea.focus();
        const cursorPosition = before.length + prefix.length + markdown.length;
        textarea.setSelectionRange(cursorPosition, cursorPosition);
      }, 0);
      return { ...current, content: nextContent };
    });
  };

  const uploadImageFile = async (file) => {
    const imageFile = normalizeImageFile(file);
    const validationError = validateImageFile(imageFile);
    if (validationError) {
      setUploadState({ error: validationError, isDragging: false, isUploading: false });
      return;
    }

    setUploadState({ error: "", isDragging: false, isUploading: true });
    try {
      const uploadedImage = await uploadWorkManualImage(imageFile);
      insertImageMarkdown(uploadedImage);
      setUploadState({ error: "", isDragging: false, isUploading: false });
    } catch {
      setUploadState({ error: "이미지 업로드에 실패했습니다.", isDragging: false, isUploading: false });
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadImageFile(file);
    }
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      uploadImageFile(file);
    } else {
      setUploadState((current) => ({ ...current, isDragging: false }));
    }
  };

  const handlePaste = (event) => {
    const items = Array.from(event.clipboardData?.items || []);
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem) {
      return;
    }
    const file = imageItem.getAsFile();
    if (file) {
      event.preventDefault();
      uploadImageFile(file);
    }
  };

  return (
    <div className="work-manual-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="work-manual-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="work-manual-form-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <form onSubmit={handleSubmit}>
          <div className="work-manual-modal-heading">
            <div>
              <span className="section-kicker">Work Manual</span>
              <h3 id="work-manual-form-title">{initialManual ? "업무설명서 수정" : "새 업무설명서"}</h3>
            </div>
            <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
              x
            </button>
          </div>
          <div className="work-manual-form-grid">
            <label className="field">
              <span>카테고리</span>
              <input
                value={form.category}
                maxLength={80}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>작성자</span>
              <input
                value={form.author}
                maxLength={80}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, author: event.target.value }))}
              />
            </label>
            <label className="work-manual-checkbox">
              <input
                type="checkbox"
                checked={form.is_pinned}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, is_pinned: event.target.checked }))}
              />
              <span>상단 고정</span>
            </label>
            <label className="field work-manual-wide-field">
              <span>제목</span>
              <input
                value={form.title}
                maxLength={200}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              />
            </label>
            <label className="field work-manual-wide-field">
              <span>본문</span>
              <textarea
                ref={textareaRef}
                value={form.content}
                rows={10}
                maxLength={10000}
                disabled={isSubmitting}
                onPaste={handlePaste}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              />
            </label>
            <div
              className={uploadState.isDragging ? "work-manual-image-upload dragging" : "work-manual-image-upload"}
              onDragEnter={(event) => {
                event.preventDefault();
                setUploadState((current) => ({ ...current, isDragging: true }));
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setUploadState((current) => ({ ...current, isDragging: false }))}
              onDrop={handleDrop}
            >
              <div>
                <strong>본문 이미지</strong>
                <span>파일 선택, 드래그앤드롭, Ctrl+V 붙여넣기 지원</span>
              </div>
              <label className="secondary-button work-manual-image-upload-button">
                이미지 선택
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif"
                  disabled={isSubmitting || uploadState.isUploading}
                  onChange={handleFileChange}
                />
              </label>
              {uploadState.isUploading ? <em>업로드 중입니다.</em> : null}
              {uploadState.error ? <p>{uploadState.error}</p> : null}
            </div>
          </div>
          {error ? <p className="work-manual-form-error">{error}</p> : null}
          <div className="work-manual-modal-actions">
            <button type="button" className="secondary-button" disabled={isSubmitting} onClick={onClose}>
              취소
            </button>
            <button
              type="submit"
              disabled={
                isSubmitting ||
                !form.category.trim() ||
                !form.title.trim() ||
                !form.content.trim() ||
                !form.author.trim()
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

function ManualContent({ content, onImageClick }) {
  const nodes = parseManualContent(formatText(content));
  return (
    <div className="work-manual-preview-content">
      {nodes.map((node, index) => {
        if (node.type === "image") {
          return (
            <button
              type="button"
              className="work-manual-content-image-button"
              key={`${node.url}-${index}`}
              onClick={() => onImageClick?.(node)}
            >
              <img src={node.url} alt={node.alt || "업무설명서 이미지"} loading="lazy" />
            </button>
          );
        }
        return <p key={`text-${index}`}>{node.text}</p>;
      })}
    </div>
  );
}

function WorkManualImageModal({ image, onClose }) {
  if (!image) {
    return null;
  }

  return (
    <div className="work-manual-image-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="work-manual-image-modal"
        role="dialog"
        aria-modal="true"
        aria-label="업무설명서 이미지 크게 보기"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="icon-button" aria-label="닫기" onClick={onClose}>
          x
        </button>
        <img src={image.url} alt={image.alt || "업무설명서 이미지"} />
      </section>
    </div>
  );
}

function WorkManualDeleteModal({ state, onClose, onConfirm }) {
  if (!state.isOpen || !state.manual) {
    return null;
  }

  return (
    <div className="work-manual-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="work-manual-delete-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="work-manual-delete-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h3 id="work-manual-delete-title">업무설명서 삭제</h3>
        <p>{formatText(state.manual.title)} 글을 목록에서 숨김 처리합니다.</p>
        {state.error ? <p className="work-manual-form-error">{state.error}</p> : null}
        <div className="work-manual-modal-actions">
          <button type="button" className="secondary-button" disabled={state.isSubmitting} onClick={onClose}>
            취소
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={state.isSubmitting}
            onClick={onConfirm}
          >
            {state.isSubmitting ? "삭제 중" : "삭제"}
          </button>
        </div>
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

function validateImageFile(file) {
  if (!file) {
    return "이미지 업로드에 실패했습니다.";
  }
  const extension = getFileExtension(file.name);
  if (!ALLOWED_IMAGE_EXTENSIONS.includes(extension)) {
    return "jpg, png, webp, gif 이미지만 업로드할 수 있습니다.";
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return "이미지는 10MB 이하만 업로드할 수 있습니다.";
  }
  return "";
}

function normalizeImageFile(file) {
  if (!file || getFileExtension(file.name)) {
    return file;
  }
  const extensionMap = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
  };
  const extension = extensionMap[file.type] || "";
  if (!extension) {
    return file;
  }
  return new File([file], `pasted-image${extension}`, { type: file.type });
}

function getFileExtension(filename) {
  const dotIndex = String(filename || "").lastIndexOf(".");
  if (dotIndex < 0) {
    return "";
  }
  return String(filename).slice(dotIndex).toLowerCase();
}

function parseManualContent(content) {
  const nodes = [];
  const imagePattern = /!\[([^\]]*)\]\(([^)\s]+)\)/g;
  let lastIndex = 0;
  let match = imagePattern.exec(content);

  while (match) {
    if (match.index > lastIndex) {
      nodes.push({ type: "text", text: content.slice(lastIndex, match.index) });
    }
    const alt = match[1] || "";
    const url = match[2] || "";
    if (isSafeManualImageUrl(url)) {
      nodes.push({ type: "image", alt, url });
    } else {
      nodes.push({ type: "text", text: match[0] });
    }
    lastIndex = imagePattern.lastIndex;
    match = imagePattern.exec(content);
  }

  if (lastIndex < content.length) {
    nodes.push({ type: "text", text: content.slice(lastIndex) });
  }

  return nodes.length ? nodes : [{ type: "text", text: "" }];
}

function isSafeManualImageUrl(url) {
  const normalizedUrl = String(url || "");
  return (
    normalizedUrl.startsWith("/uploads/work_manuals/images/") &&
    !normalizedUrl.includes("..") &&
    !normalizedUrl.includes("\\") &&
    /\.(jpe?g|png|webp|gif)$/i.test(normalizedUrl)
  );
}

function hasValidAdminAuth() {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const storedValue = window.sessionStorage.getItem(ADMIN_AUTH_STORAGE_KEY);
    if (!storedValue) {
      return false;
    }
    const parsedValue = JSON.parse(storedValue);
    const expiresAt = Date.parse(parsedValue?.expires_at || "");
    if (!parsedValue?.token || !String(parsedValue.token).includes(".") || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
      window.sessionStorage.removeItem(ADMIN_AUTH_STORAGE_KEY);
      return false;
    }
    return true;
  } catch {
    window.sessionStorage.removeItem(ADMIN_AUTH_STORAGE_KEY);
    return false;
  }
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default WorkManualPage;
