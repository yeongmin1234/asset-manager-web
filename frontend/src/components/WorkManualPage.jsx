import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createWorkManual,
  deleteWorkManual,
  getWorkManual,
  getWorkManuals,
  updateWorkManual,
} from "../api/client.js";

const EMPTY_MANUAL_FORM = {
  category: "일반",
  title: "",
  content: "",
  author: "관리자",
  is_pinned: false,
  admin_password: "",
};

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
    adminPassword: "",
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
      adminPassword: "",
      error: "",
      isOpen: true,
      isSubmitting: false,
      manual,
    });
  };

  const closeDelete = () => {
    setDeleteState({
      adminPassword: "",
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
      await deleteWorkManual(deleteState.manual.id, deleteState.adminPassword);
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
        <button type="button" onClick={openCreateForm}>
          새 글 작성
        </button>
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
        onChangePassword={(adminPassword) =>
          setDeleteState((current) => ({ ...current, adminPassword }))
        }
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

function WorkManualPreview({ isLoading, manual, onClose, onDelete, onEdit }) {
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
        <div className="work-manual-preview-content">{formatText(manual.content)}</div>
      )}
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
    </aside>
  );
}

function WorkManualFormModal({ error, initialManual, isOpen, isSubmitting, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_MANUAL_FORM);

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
      admin_password: "",
    });
  }, [initialManual, isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit?.(form);
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
                value={form.content}
                rows={10}
                maxLength={10000}
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              />
            </label>
            <label className="field work-manual-wide-field">
              <span>관리자 비밀번호</span>
              <input
                type="password"
                value={form.admin_password}
                autoComplete="current-password"
                disabled={isSubmitting}
                onChange={(event) => setForm((current) => ({ ...current, admin_password: event.target.value }))}
              />
            </label>
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
                !form.author.trim() ||
                !form.admin_password
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

function WorkManualDeleteModal({ state, onChangePassword, onClose, onConfirm }) {
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
        <label className="field">
          <span>관리자 비밀번호</span>
          <input
            type="password"
            value={state.adminPassword}
            autoComplete="current-password"
            disabled={state.isSubmitting}
            onChange={(event) => onChangePassword?.(event.target.value)}
          />
        </label>
        {state.error ? <p className="work-manual-form-error">{state.error}</p> : null}
        <div className="work-manual-modal-actions">
          <button type="button" className="secondary-button" disabled={state.isSubmitting} onClick={onClose}>
            취소
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={state.isSubmitting || !state.adminPassword}
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
