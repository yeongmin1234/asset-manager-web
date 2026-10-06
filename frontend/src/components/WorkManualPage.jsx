import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createWorkManual,
  deleteWorkManual,
  getWorkManual,
  getWorkManuals,
  updateWorkManual,
  uploadWorkManualImage,
  fetchPrivateImage,
} from "../api/client.js";
import PrivateImage from "./PrivateImage.jsx";
import {
  BOARD_SORT_OPTIONS,
  SORT_VALUES,
  SortSelect,
  sortItems,
} from "../utils/sortOptions.jsx";
import AttachmentPanel from "./AttachmentPanel.jsx";

const EMPTY_MANUAL_FORM = {
  category: "다우오피스",
  title: "",
  content: "",
  author: "관리자",
  is_pinned: false,
};

const WORK_MANUAL_CATEGORIES = ["다우오피스", "전산", "백업메뉴얼"];
const WORK_MANUAL_ALL_CATEGORY = "";

const ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;
const BASE64_IMAGE_PATTERN = /data:image\/[a-z0-9.+-]+;base64,[^\s"'<)]+/gi;

function WorkManualPage({ currentUser, initialManualId = null }) {
  const [manuals, setManuals] = useState([]);
  const [listState, setListState] = useState({ error: "", isLoading: false });
  const [filters, setFilters] = useState({ keyword: "", category: "다우오피스" });
  const [sortValue, setSortValue] = useState(SORT_VALUES.latest);
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
    if (!initialManualId) {
      return;
    }
    handleSelectManual({ id: initialManualId }, { updateHistory: false });
  }, [initialManualId]);

  useEffect(() => {
    if (filters.category !== "다우오피스" || manuals.length === 0) {
      return;
    }
    const hasOfficialCategoryManual = manuals.some((manual) =>
      WORK_MANUAL_CATEGORIES.includes(manual.category),
    );
    if (!hasOfficialCategoryManual) {
      setFilters((current) => ({ ...current, category: WORK_MANUAL_ALL_CATEGORY }));
    }
  }, [filters.category, manuals]);

  const categoryTabs = useMemo(() => {
    const counts = WORK_MANUAL_CATEGORIES.reduce(
      (accumulator, category) => ({ ...accumulator, [category]: 0 }),
      {},
    );
    manuals.forEach((manual) => {
      if (WORK_MANUAL_CATEGORIES.includes(manual.category)) {
        counts[manual.category] += 1;
      }
    });
    return [
      { label: "전체", value: WORK_MANUAL_ALL_CATEGORY, count: manuals.length },
      ...WORK_MANUAL_CATEGORIES.map((category) => ({
        label: category,
        value: category,
        count: counts[category] || 0,
      })),
    ];
  }, [manuals]);

  const filteredManuals = useMemo(() => {
    const keyword = filters.keyword.trim().toLowerCase();
    const nextManuals = manuals.filter((manual) => {
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
    return sortItems(nextManuals, sortValue, {
      created: ["created_at"],
      updated: ["updated_at", "created_at"],
      title: ["title"],
    });
  }, [filters, manuals, sortValue]);

  useEffect(() => {
    if (!selectedManual || !filters.category) {
      return;
    }
    if (selectedManual.category !== filters.category) {
      setSelectedManual(null);
      if (typeof window !== "undefined" && window.location.pathname !== "/work-manuals") {
        window.history.pushState({}, "", "/work-manuals");
      }
    }
  }, [filters.category, selectedManual]);

  const handleSelectManual = async (manual, { updateHistory = true } = {}) => {
    setDetailState({ error: "", isLoading: true });
    try {
      const detail = await getWorkManual(manual.id);
      setSelectedManual(detail);
      setManuals((current) =>
        current.map((item) => (item.id === detail.id ? { ...item, ...detail } : item)),
      );
      if (updateHistory && typeof window !== "undefined") {
        const detailPath = `/work-manuals/${detail.id}`;
        if (window.location.pathname !== detailPath) {
          window.history.pushState({}, "", detailPath);
        }
      }
      setDetailState({ error: "", isLoading: false });
    } catch (error) {
      setDetailState({ error: error.message, isLoading: false });
    }
  };

  const closeManual = () => {
    setSelectedManual(null);
    if (typeof window !== "undefined" && window.location.pathname !== "/work-manuals") {
      window.history.pushState({}, "", "/work-manuals");
    }
  };

  const openCreateForm = () => {
    setFormState({ error: "", initialManual: null, isOpen: true, isSubmitting: false });
  };

  const openEditForm = (manual) => {
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
        if (typeof window !== "undefined" && window.location.pathname !== "/work-manuals") {
          window.history.replaceState({}, "", "/work-manuals");
        }
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
        <button type="button" onClick={openCreateForm}>
          새 글 작성
        </button>
      </div>

      <div className="work-manual-category-tabs" role="tablist" aria-label="업무설명서 카테고리">
        {categoryTabs.map((tab) => {
          const active = filters.category === tab.value;
          return (
            <button
              type="button"
              key={tab.label}
              className={active ? "work-manual-category-tab active" : "work-manual-category-tab"}
              role="tab"
              aria-selected={active}
              onClick={() => setFilters((current) => ({ ...current, category: tab.value }))}
            >
              <span>{tab.label}</span>
              <strong>{Number(tab.count || 0).toLocaleString("ko-KR")}</strong>
            </button>
          );
        })}
      </div>

      <section className="work-manual-controls" aria-label="업무설명서 검색 및 필터">
        <label>
          <span>검색</span>
          <input
            value={filters.keyword}
            placeholder="제목, 내용, 카테고리"
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
          />
        </label>
        <button
          type="button"
          className="secondary-button"
          onClick={() => setFilters((current) => ({ ...current, keyword: "" }))}
          disabled={!filters.keyword}
        >
          검색 초기화
        </button>
        <button type="button" className="secondary-button" onClick={loadManuals}>
          새로고침
        </button>
        <SortSelect
          value={sortValue}
          options={BOARD_SORT_OPTIONS}
          onChange={setSortValue}
        />
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
            onClose={closeManual}
            onDelete={openDelete}
            onEdit={openEditForm}
            currentUser={currentUser}
          />
        ) : null}
      </div>

      <WorkManualFormModal
        error={formState.error}
        initialCategory={WORK_MANUAL_CATEGORIES.includes(filters.category) ? filters.category : "다우오피스"}
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
                  <button
                    type="button"
                    className="work-manual-title-link"
                    title={formatText(manual.title)}
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectManual?.(manual);
                    }}
                  >
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

function WorkManualPreview({ currentUser, isLoading, manual, onClose, onDelete, onEdit }) {
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
      <AttachmentPanel
        canManage={currentUser?.role === "admin"}
        entityId={manual.id}
        entityType="work_manual"
        title="일반 첨부파일"
      />
      <div className="work-manual-preview-actions">
        <button type="button" className="secondary-button" onClick={() => onEdit?.(manual)}>
          수정
        </button>
        <button type="button" className="danger-button" onClick={() => onDelete?.(manual)}>
          삭제
        </button>
        <button type="button" className="secondary-button" onClick={onClose}>
          닫기
        </button>
      </div>
      <WorkManualImageModal image={previewImage} onClose={() => setPreviewImage(null)} />
    </aside>
  );
}

function WorkManualFormModal({ error, initialCategory, initialManual, isOpen, isSubmitting, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_MANUAL_FORM);
  const [editorImageAction, setEditorImageAction] = useState(null);
  const [uploadState, setUploadState] = useState({ error: "", isDragging: false, isUploading: false });
  const editorRef = useRef(null);
  const editorHydrationKeyRef = useRef("");
  const fileInputRef = useRef(null);
  const savedRangeRef = useRef(null);
  const selectedImageRef = useRef(null);
  const editorImageUrlsRef = useRef([]);

  useEffect(() => {
    if (!isOpen) {
      setForm(EMPTY_MANUAL_FORM);
      return;
    }
    setForm({
      category: initialManual?.category || initialCategory || "다우오피스",
      title: initialManual?.title || "",
      content: normalizeContentForEditor(initialManual?.content || ""),
      author: initialManual?.author || "관리자",
      is_pinned: Boolean(initialManual?.is_pinned),
    });
  }, [initialCategory, initialManual, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      editorHydrationKeyRef.current = "";
      editorImageUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      editorImageUrlsRef.current = [];
      return;
    }
    if (!editorRef.current) {
      return;
    }
    const hydrationKey = initialManual?.id ? `manual-${initialManual.id}` : "new-manual";
    if (editorHydrationKeyRef.current === hydrationKey) {
      return;
    }
    editorImageUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    editorImageUrlsRef.current = [];
    const nextContent = normalizeContentForEditor(initialManual?.content || "");
    editorRef.current.innerHTML = prepareEditorImageHtml(nextContent);
    hydrateEditorImages(editorRef.current, editorImageUrlsRef.current);
    editorHydrationKeyRef.current = hydrationKey;
    setForm((current) => ({ ...current, content: nextContent }));
  }, [initialManual, isOpen]);

  useEffect(() => {
    if (!isOpen) {
      selectedImageRef.current?.classList.remove("work-manual-editor-image-selected");
      selectedImageRef.current = null;
      setEditorImageAction(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!editorImageAction) {
      return undefined;
    }
    const handleDocumentMouseDown = (event) => {
      const target = event.target;
      if (
        editorRef.current?.contains(target) ||
        target?.closest?.(".work-manual-editor-image-delete")
      ) {
        return;
      }
      clearSelectedEditorImage();
    };
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        clearSelectedEditorImage();
      }
    };
    document.addEventListener("mousedown", handleDocumentMouseDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleDocumentMouseDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [editorImageAction]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const content = sanitizeManualHtml(editorRef.current?.innerHTML || "");
    onSubmit?.({ ...form, content });
  };

  const categoryOptions = useMemo(() => {
    const currentCategory = String(form.category || "").trim();
    if (currentCategory && !WORK_MANUAL_CATEGORIES.includes(currentCategory)) {
      return [currentCategory, ...WORK_MANUAL_CATEGORIES];
    }
    return WORK_MANUAL_CATEGORIES;
  }, [form.category]);

  const syncEditorContent = () => {
    setForm((current) => ({
      ...current,
      content: sanitizeManualHtml(editorRef.current?.innerHTML || ""),
    }));
  };

  const clearSelectedEditorImage = () => {
    selectedImageRef.current?.classList.remove("work-manual-editor-image-selected");
    selectedImageRef.current = null;
    setEditorImageAction(null);
  };

  const selectEditorImage = (imageElement) => {
    if (!editorRef.current || !imageElement) {
      return;
    }
    selectedImageRef.current?.classList.remove("work-manual-editor-image-selected");
    selectedImageRef.current = imageElement;
    imageElement.classList.add("work-manual-editor-image-selected");
    const editorRect = editorRef.current.getBoundingClientRect();
    const imageRect = imageElement.getBoundingClientRect();
    setEditorImageAction({
      left: Math.max(8, imageRect.right - editorRect.left - 42),
      top: Math.max(8, imageRect.top - editorRect.top + editorRef.current.scrollTop + 8),
    });
  };

  const saveSelection = () => {
    const selection = window.getSelection();
    if (
      !selection ||
      selection.rangeCount === 0 ||
      !editorRef.current?.contains(selection.anchorNode) ||
      !editorRef.current?.contains(selection.focusNode)
    ) {
      return;
    }
    savedRangeRef.current = selection.getRangeAt(0).cloneRange();
  };

  const focusEditor = () => {
    if (!editorRef.current) {
      return;
    }
    try {
      editorRef.current.focus({ preventScroll: true });
    } catch {
      editorRef.current.focus();
    }
  };

  const hasEditorSelection = () => {
    const selection = window.getSelection();
    return Boolean(
      selection &&
      selection.rangeCount > 0 &&
      editorRef.current?.contains(selection.anchorNode) &&
      editorRef.current?.contains(selection.focusNode),
    );
  };

  const hasSavedSelection = () =>
    Boolean(
      savedRangeRef.current &&
      editorRef.current?.contains(savedRangeRef.current.commonAncestorContainer),
    );

  const restoreSelection = ({ preferCurrent = false } = {}) => {
    const shouldKeepCurrentSelection = preferCurrent && hasEditorSelection();
    focusEditor();
    const selection = window.getSelection();
    if (!selection) {
      return;
    }
    if (shouldKeepCurrentSelection) {
      return;
    }
    selection.removeAllRanges();
    if (hasSavedSelection()) {
      selection.addRange(savedRangeRef.current);
      return;
    }
    const range = document.createRange();
    range.selectNodeContents(editorRef.current);
    range.collapse(false);
    selection.addRange(range);
  };

  const moveSelectionToPoint = (clientX, clientY) => {
    if (!editorRef.current) {
      return;
    }
    let range = null;
    if (document.caretRangeFromPoint) {
      range = document.caretRangeFromPoint(clientX, clientY);
    } else if (document.caretPositionFromPoint) {
      const position = document.caretPositionFromPoint(clientX, clientY);
      if (position) {
        range = document.createRange();
        range.setStart(position.offsetNode, position.offset);
      }
    }
    if (!range || !editorRef.current.contains(range.startContainer)) {
      restoreSelection();
      return;
    }
    range.collapse(true);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    savedRangeRef.current = range.cloneRange();
  };

  const applyFormat = (command) => {
    if (!editorRef.current) {
      return;
    }
    if (!hasEditorSelection()) {
      focusEditor();
      if (hasSavedSelection()) {
        restoreSelection();
      }
    }
    document.execCommand(command, false, null);
    syncEditorContent();
    saveSelection();
  };

  const runEditorCommand = (command, value = null) => {
    restoreSelection({ preferCurrent: true });
    document.execCommand(command, false, value);
    syncEditorContent();
    saveSelection();
  };

  const insertHtmlAtCursor = (html) => {
    restoreSelection();
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return;
    }
    const range = selection.getRangeAt(0);
    range.deleteContents();
    const template = document.createElement("template");
    template.innerHTML = html;
    const fragment = template.content;
    const lastNode = fragment.lastChild;
    range.insertNode(fragment);
    if (lastNode) {
      range.setStartAfter(lastNode);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    syncEditorContent();
    saveSelection();
  };

  const handleToolbarMouseDown = (event) => {
    event.preventDefault();
    saveSelection();
  };

  const handleEditorKeyDown = (event) => {
    if (event.key === "Escape") {
      clearSelectedEditorImage();
      return;
    }
    if (!event.ctrlKey && !event.metaKey) {
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "b") {
      event.preventDefault();
      applyFormat("bold");
      return;
    }
    if (key === "u") {
      event.preventDefault();
      applyFormat("underline");
      return;
    }
    if (key === "i") {
      event.preventDefault();
      applyFormat("italic");
    }
  };

  const insertUploadedImage = async (image) => {
    if (!isSafeManualImageUrl(image?.url)) {
      return;
    }
    const objectUrl = URL.createObjectURL(await fetchPrivateImage(image.url));
    editorImageUrlsRef.current.push(objectUrl);
    insertHtmlAtCursor(`<img src="${objectUrl}" data-upload-src="${image.url}" alt="이미지"><p><br></p>`);
  };

  const uploadImageAndInsert = async (files) => {
    const imageFiles = Array.from(files || []).filter(Boolean);
    if (imageFiles.length === 0) {
      return;
    }

    setUploadState({ error: "", isDragging: false, isUploading: true });
    let lastError = "";
    try {
      for (const file of imageFiles) {
        const imageFile = normalizeImageFile(file);
        const validationError = validateImageFile(imageFile);
        if (validationError) {
          lastError = validationError;
          continue;
        }
        const uploadedImage = await uploadWorkManualImage(imageFile);
        await insertUploadedImage(uploadedImage);
      }
      setUploadState({ error: lastError, isDragging: false, isUploading: false });
    } catch {
      setUploadState({ error: "이미지 업로드에 실패했습니다.", isDragging: false, isUploading: false });
    }
  };

  const handleFileChange = (event) => {
    uploadImageAndInsert(event.target.files);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    moveSelectionToPoint(event.clientX, event.clientY);
    const files = Array.from(event.dataTransfer.files || []);
    if (files.length > 0) {
      uploadImageAndInsert(files);
    } else {
      setUploadState((current) => ({ ...current, isDragging: false }));
    }
  };

  const handlePaste = (event) => {
    const items = Array.from(event.clipboardData?.items || []);
    const imageFiles = items
      .filter((item) => item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter(Boolean);
    if (imageFiles.length > 0) {
      event.preventDefault();
      saveSelection();
      uploadImageAndInsert(imageFiles);
      return;
    }
    const text = event.clipboardData?.getData("text/plain") || "";
    if (text) {
      event.preventDefault();
      insertHtmlAtCursor(escapeHtml(text).replace(/\n/g, "<br>"));
    }
  };

  const handleEditorMouseDown = (event) => {
    if (event.target?.tagName?.toLowerCase() !== "img") {
      clearSelectedEditorImage();
      return;
    }
    const scrollY = window.scrollY;
    event.preventDefault();
    event.stopPropagation();
    selectEditorImage(event.target);
    window.requestAnimationFrame(() => window.scrollTo(window.scrollX, scrollY));
  };

  const handleEditorClick = (event) => {
    if (event.target?.tagName?.toLowerCase() !== "img") {
      return;
    }
    const scrollY = window.scrollY;
    event.preventDefault();
    event.stopPropagation();
    window.requestAnimationFrame(() => window.scrollTo(window.scrollX, scrollY));
  };

  const handleDeleteSelectedImage = (event) => {
    const scrollY = window.scrollY;
    const editorScrollTop = editorRef.current?.scrollTop || 0;
    event.preventDefault();
    event.stopPropagation();
    const imageElement = selectedImageRef.current;
    if (!imageElement || !editorRef.current?.contains(imageElement)) {
      clearSelectedEditorImage();
      return;
    }
    if (!window.confirm("이 이미지를 삭제할까요?")) {
      window.requestAnimationFrame(() => window.scrollTo(window.scrollX, scrollY));
      return;
    }
    imageElement.remove();
    clearSelectedEditorImage();
    syncEditorContent();
    window.requestAnimationFrame(() => {
      if (editorRef.current) {
        editorRef.current.scrollTop = editorScrollTop;
      }
      window.scrollTo(window.scrollX, scrollY);
    });
  };

  if (!isOpen) {
    return null;
  }

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
              <select
                value={form.category}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
              >
                {categoryOptions.map((category) => (
                  <option key={category} value={category}>
                    {WORK_MANUAL_CATEGORIES.includes(category) ? category : `${category} (기존)`}
                  </option>
                ))}
              </select>
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
            <div className="field work-manual-wide-field">
              <span>본문</span>
              <div className="work-manual-format-toolbar" aria-label="본문 서식 도구">
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => applyFormat("bold")}>굵게</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => applyFormat("underline")}>밑줄</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => applyFormat("italic")}>기울임</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => runEditorCommand("formatBlock", "h3")}>제목</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => runEditorCommand("insertUnorderedList")}>글머리</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => runEditorCommand("insertOrderedList")}>번호</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => insertHtmlAtCursor("<hr>")}>구분선</button>
                <button type="button" onMouseDown={handleToolbarMouseDown} onClick={() => fileInputRef.current?.click()}>이미지</button>
              </div>
              <div className="work-manual-editor-shell">
                <div
                  ref={editorRef}
                  className={uploadState.isDragging ? "work-manual-rich-editor dragging" : "work-manual-rich-editor"}
                  contentEditable={true}
                  role="textbox"
                  aria-multiline="true"
                  aria-disabled={isSubmitting}
                  tabIndex={0}
                  suppressContentEditableWarning
                  onBlur={syncEditorContent}
                  onClick={handleEditorClick}
                  onInput={syncEditorContent}
                  onKeyDown={handleEditorKeyDown}
                  onKeyUp={saveSelection}
                  onMouseDown={handleEditorMouseDown}
                  onMouseUp={saveSelection}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setUploadState((current) => ({ ...current, isDragging: true }));
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setUploadState((current) => ({ ...current, isDragging: false }))}
                  onDrop={handleDrop}
                  onPaste={handlePaste}
                />
                {editorImageAction ? (
                  <button
                    type="button"
                    className="work-manual-editor-image-delete"
                    style={{ left: `${editorImageAction.left}px`, top: `${editorImageAction.top}px` }}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                    }}
                    onClick={handleDeleteSelectedImage}
                  >
                    삭제
                  </button>
                ) : null}
              </div>
            </div>
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
                  ref={fileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif"
                  disabled={isSubmitting || uploadState.isUploading}
                  onChange={handleFileChange}
                />
              </label>
              {uploadState.isUploading ? <em>이미지 업로드 중...</em> : null}
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
  const nodes = renderSanitizedManualHtml(normalizeContentForRender(formatText(content)), onImageClick);
  return (
    <div className="work-manual-preview-content">
      {nodes.length ? nodes : <p className="work-manual-blank-line" />}
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

function prepareEditorImageHtml(html) {
  const documentValue = new DOMParser().parseFromString(`<div>${html}</div>`, "text/html");
  const root = documentValue.body.firstChild;
  root.querySelectorAll("img").forEach((image) => {
    const source = image.getAttribute("src") || "";
    if (isSafeManualImageUrl(source)) {
      image.setAttribute("data-upload-src", source);
      image.removeAttribute("src");
    }
  });
  return root.innerHTML;
}

function hydrateEditorImages(editor, urls) {
  editor.querySelectorAll("img[data-upload-src]").forEach((image) => {
    fetchPrivateImage(image.getAttribute("data-upload-src")).then((blob) => {
      if (!image.isConnected) return;
      const objectUrl = URL.createObjectURL(blob);
      urls.push(objectUrl);
      image.src = objectUrl;
    }).catch(() => {});
  });
}

function normalizeContentForEditor(content) {
  return normalizeContentForRender(content || "");
}

function normalizeContentForRender(content) {
  const value = String(content || "");
  if (hasHtmlMarkup(value)) {
    return sanitizeManualHtml(value);
  }
  return sanitizeManualHtml(markdownToHtml(value));
}

function hasHtmlMarkup(value) {
  return /<\/?(p|br|strong|b|em|i|u|h2|h3|ul|ol|li|hr|img|div|span)\b/i.test(String(value || ""));
}

function sanitizeManualHtml(html) {
  if (typeof window === "undefined" || typeof DOMParser === "undefined") {
    return "";
  }
  const normalizedHtml = String(html || "").replace(BASE64_IMAGE_PATTERN, "");
  const parser = new DOMParser();
  const documentValue = parser.parseFromString(`<div>${normalizedHtml}</div>`, "text/html");
  return Array.from(documentValue.body.firstChild?.childNodes || [])
    .map((node) => sanitizeManualNodeToHtml(node))
    .join("");
}

function sanitizeManualNodeToHtml(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return escapeHtml(node.textContent || "");
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return "";
  }

  const tagName = node.tagName.toLowerCase();
  const childrenHtml = Array.from(node.childNodes)
    .map((child) => sanitizeManualNodeToHtml(child))
    .join("");

  if (tagName === "br") {
    return "<br>";
  }
  if (tagName === "hr") {
    return "<hr>";
  }
  if (tagName === "img") {
    const src = node.getAttribute("data-upload-src") || node.getAttribute("src") || "";
    if (!isSafeManualImageUrl(src)) {
      return "";
    }
    const alt = escapeHtml(node.getAttribute("alt") || "업무설명서 이미지");
    return `<img src="${src}" alt="${alt}">`;
  }

  const tagMap = {
    b: "strong",
    strong: "strong",
    i: "em",
    em: "em",
    u: "u",
    h2: "h2",
    h3: "h3",
    ul: "ul",
    ol: "ol",
    li: "li",
    p: "p",
    div: "p",
  };
  const safeTagName = tagMap[tagName];
  if (!safeTagName) {
    return childrenHtml;
  }
  return `<${safeTagName}>${childrenHtml}</${safeTagName}>`;
}

function markdownToHtml(content) {
  const lines = String(content || "").split("\n");
  const html = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      html.push("<p><br></p>");
      index += 1;
      continue;
    }
    if (line.trim() === "---") {
      html.push("<hr>");
      index += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      html.push(`<h3>${renderInlineMarkdownToHtml(line.slice(3))}</h3>`);
      index += 1;
      continue;
    }
    if (/^\s*-\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*-\s+/.test(lines[index])) {
        items.push(`<li>${renderInlineMarkdownToHtml(lines[index].replace(/^\s*-\s+/, ""))}</li>`);
        index += 1;
      }
      html.push(`<ul>${items.join("")}</ul>`);
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*\d+\.\s+/.test(lines[index])) {
        items.push(`<li>${renderInlineMarkdownToHtml(lines[index].replace(/^\s*\d+\.\s+/, ""))}</li>`);
        index += 1;
      }
      html.push(`<ol>${items.join("")}</ol>`);
      continue;
    }
    html.push(`<p>${renderInlineMarkdownToHtml(line)}</p>`);
    index += 1;
  }

  return html.join("");
}

function renderInlineMarkdownToHtml(text) {
  const parts = [];
  const pattern = /(!\[([^\]]*)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|<u>([^<]+)<\/u>|\*([^*]+)\*)/g;
  let lastIndex = 0;
  let match = pattern.exec(text);

  while (match) {
    if (match.index > lastIndex) {
      parts.push(escapeHtml(text.slice(lastIndex, match.index)));
    }
    if (match[1]?.startsWith("![")) {
      const alt = escapeHtml(match[2] || "업무설명서 이미지");
      const url = match[3] || "";
      parts.push(isSafeManualImageUrl(url) ? `<img src="${url}" alt="${alt}">` : escapeHtml(match[0]));
    } else if (match[4]) {
      parts.push(`<strong>${escapeHtml(match[4])}</strong>`);
    } else if (match[5]) {
      parts.push(`<u>${escapeHtml(match[5])}</u>`);
    } else if (match[6]) {
      parts.push(`<em>${escapeHtml(match[6])}</em>`);
    }
    lastIndex = pattern.lastIndex;
    match = pattern.exec(text);
  }

  if (lastIndex < text.length) {
    parts.push(escapeHtml(text.slice(lastIndex)));
  }
  return parts.join("");
}

function renderSanitizedManualHtml(html, onImageClick) {
  if (typeof window === "undefined" || typeof DOMParser === "undefined") {
    return [];
  }
  const sanitizedHtml = sanitizeManualHtml(html);
  const parser = new DOMParser();
  const documentValue = parser.parseFromString(`<div>${sanitizedHtml}</div>`, "text/html");
  return Array.from(documentValue.body.firstChild?.childNodes || []).map((node, index) =>
    renderManualDomNode(node, `manual-${index}`, onImageClick),
  ).filter(Boolean);
}

function renderManualDomNode(node, key, onImageClick) {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const tagName = node.tagName.toLowerCase();
  if (tagName === "br") {
    return <br key={key} />;
  }
  if (tagName === "hr") {
    return <hr key={key} />;
  }
  if (tagName === "img") {
    const src = node.getAttribute("src") || "";
    if (!isSafeManualImageUrl(src)) {
      return null;
    }
    const alt = node.getAttribute("alt") || "업무설명서 이미지";
    return (
      <button
        type="button"
        className="work-manual-content-image-button"
        key={key}
      >
        <PrivateImage path={src} alt={alt} loading="lazy" onClick={(url) => onImageClick?.({ alt, url })} />
      </button>
    );
  }

  const children = Array.from(node.childNodes).map((child, index) =>
    renderManualDomNode(child, `${key}-${index}`, onImageClick),
  );
  const props = { key };
  if (tagName === "p" && !node.textContent && node.querySelector("br")) {
    props.className = "work-manual-blank-line";
  }
  const allowedTags = ["p", "strong", "b", "em", "i", "u", "h2", "h3", "ul", "ol", "li"];
  if (!allowedTags.includes(tagName)) {
    return <React.Fragment key={key}>{children}</React.Fragment>;
  }
  return React.createElement(tagName, props, children);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function validateImageFile(file) {
  if (!file) {
    return "이미지 업로드에 실패했습니다.";
  }
  if (file.type && !file.type.startsWith("image/")) {
    return "이미지 파일만 업로드할 수 있습니다.";
  }
  const extension = getFileExtension(file.name);
  if (!ALLOWED_IMAGE_EXTENSIONS.includes(extension)) {
    return "jpg, jpeg, png, webp, gif 이미지만 업로드할 수 있습니다.";
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

function isSafeManualImageUrl(url) {
  const normalizedUrl = String(url || "");
  return (
    (normalizedUrl.startsWith("/uploads/work_manuals/images/") ||
      normalizedUrl.startsWith("/work-manuals/images/")) &&
    !normalizedUrl.includes("..") &&
    !normalizedUrl.includes("\\") &&
    /\.(jpe?g|png|webp|gif)$/i.test(normalizedUrl)
  );
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
