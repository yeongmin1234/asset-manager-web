import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  API_BASE_URL,
  createBeverageOrder,
  deleteBeverageOrder,
  getBeverageOrder,
  getBeverageOrderSummary,
  getBeverageOrders,
  updateBeverageOrder,
} from "../api/client.js";

const INITIAL_FILTERS = {
  order_month: "",
  order_type: "",
  keyword: "",
};

const INITIAL_SUMMARY = {
  total: 0,
  this_month: 0,
  total_amount_total: 0,
  this_month_amount: 0,
  beverage: 0,
  supplies: 0,
};

const INITIAL_FORM = {
  order_type: "beverage",
  memo: "",
  total_amount: "",
  image: null,
};

const BEVERAGE_ORDER_TYPES = [
  { value: "beverage", label: "음료" },
  { value: "supplies", label: "소모품" },
];

function BeverageOrderPage() {
  const [orders, setOrders] = useState([]);
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [editingOrder, setEditingOrder] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [previewUrl, setPreviewUrl] = useState("");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [listState, setListState] = useState({ isLoading: false, error: "" });
  const [summaryState, setSummaryState] = useState({ isLoading: false, error: "" });
  const [detailState, setDetailState] = useState({ isLoading: false, error: "" });
  const [submitState, setSubmitState] = useState({ isSubmitting: false, message: "", error: "" });

  const loadOrders = useCallback(async () => {
    setListState({ isLoading: true, error: "" });
    try {
      setOrders(await getBeverageOrders(filters));
      setListState({ isLoading: false, error: "" });
    } catch (error) {
      setOrders([]);
      setListState({ isLoading: false, error: error.message });
    }
  }, [filters]);

  const loadSummary = useCallback(async () => {
    setSummaryState({ isLoading: true, error: "" });
    try {
      setSummary({ ...INITIAL_SUMMARY, ...(await getBeverageOrderSummary()) });
      setSummaryState({ isLoading: false, error: "" });
    } catch (error) {
      setSummary(INITIAL_SUMMARY);
      setSummaryState({ isLoading: false, error: error.message });
    }
  }, []);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const monthOptions = useMemo(() => {
    const values = new Set();
    orders.forEach((order) => {
      if (order.order_month) {
        values.add(order.order_month);
      }
    });
    return Array.from(values).sort().reverse();
  }, [orders]);

  const expectedTitle = useMemo(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${year}-${month}-${day} 음료 주문`;
  }, []);

  const expectedMonth = expectedTitle.slice(0, 7);

  const resetForm = () => {
    setForm(INITIAL_FORM);
    setEditingOrder(null);
    setIsFormOpen(false);
    setSubmitState({ isSubmitting: false, message: "", error: "" });
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl("");
    }
  };

  const openCreateForm = () => {
    resetForm();
    setIsFormOpen(true);
  };

  const openEditForm = (order) => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setEditingOrder(order);
    setSelectedOrder(order);
    setForm({
      order_type: normalizeOrderType(order.order_type),
      memo: order.memo || "",
      total_amount: String(order.total_amount ?? ""),
      image: null,
    });
    setPreviewUrl("");
    setIsFormOpen(true);
    setSubmitState({ isSubmitting: false, message: "", error: "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const setImageFile = (file) => {
    if (!file) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      setSubmitState({ isSubmitting: false, message: "", error: "이미지 파일만 첨부할 수 있습니다." });
      return;
    }
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setForm((current) => ({ ...current, image: file }));
    setPreviewUrl(URL.createObjectURL(file));
    setSubmitState((current) => ({ ...current, message: "", error: "" }));
  };

  const handlePaste = (event) => {
    const files = Array.from(event.clipboardData?.files || []);
    const imageFile = files.find((file) => file.type.startsWith("image/"));
    if (imageFile) {
      event.preventDefault();
      setImageFile(imageFile);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!editingOrder && !form.image) {
      setSubmitState({ isSubmitting: false, message: "", error: "쿠팡 주문 캡처 이미지를 첨부해주세요." });
      return;
    }

    const formData = new FormData();
    formData.append("order_type", normalizeOrderType(form.order_type));
    formData.append("memo", form.memo);
    formData.append("total_amount", form.total_amount);
    if (form.image) {
      formData.append("image", form.image);
    }

    setSubmitState({ isSubmitting: true, message: "", error: "" });
    try {
      const savedOrder = editingOrder
        ? await updateBeverageOrder(editingOrder.id, formData)
        : await createBeverageOrder(formData);
      setSelectedOrder(savedOrder);
      resetForm();
      setSubmitState({
        isSubmitting: false,
        message: editingOrder ? "게시글을 수정했습니다." : "게시글을 등록했습니다.",
        error: "",
      });
      await Promise.all([loadOrders(), loadSummary()]);
    } catch (error) {
      setSubmitState({ isSubmitting: false, message: "", error: error.message });
    }
  };

  const handleSelectOrder = async (order) => {
    setDetailState({ isLoading: true, error: "" });
    try {
      setSelectedOrder(await getBeverageOrder(order.id));
      setDetailState({ isLoading: false, error: "" });
    } catch (error) {
      setDetailState({ isLoading: false, error: error.message });
    }
  };

  const handleDelete = async (order) => {
    const confirmed = window.confirm(`${order.title || "선택한 게시글"}을 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    await deleteBeverageOrder(order.id);
    if (selectedOrder?.id === order.id) {
      setSelectedOrder(null);
    }
    if (editingOrder?.id === order.id) {
      resetForm();
    }
    await Promise.all([loadOrders(), loadSummary()]);
  };

  return (
    <div className="beverage-page">
      <div className="portal-screen-heading beverage-heading">
        <div>
          <h2>음료주문기록</h2>
          <p>쿠팡 등에서 주문한 음료 주문 캡처를 게시글로 관리합니다.</p>
        </div>
        <button type="button" className="primary-action" onClick={openCreateForm}>
          글쓰기
        </button>
      </div>

      <BeverageOrderStats
        error={summaryState.error}
        isLoading={summaryState.isLoading}
        summary={summary}
      />

      {isFormOpen && (
        <BeverageOrderForm
          editingOrder={editingOrder}
          expectedMonth={expectedMonth}
          expectedTitle={expectedTitle}
          form={form}
          previewUrl={previewUrl}
          submitState={submitState}
          onCancel={resetForm}
          onChangeAmount={(value) => setForm((current) => ({ ...current, total_amount: value }))}
          onChangeMemo={(value) => setForm((current) => ({ ...current, memo: value }))}
          onChangeOrderType={(value) => setForm((current) => ({ ...current, order_type: normalizeOrderType(value) }))}
          onFileChange={setImageFile}
          onPaste={handlePaste}
          onSubmit={handleSubmit}
        />
      )}

      {submitState.message && !isFormOpen && (
        <span className="inline-success beverage-submit-message">{submitState.message}</span>
      )}

      <section className="beverage-content-grid">
        <BeverageOrderList
          editingOrderId={editingOrder?.id || null}
          error={listState.error}
          filters={filters}
          isLoading={listState.isLoading}
          monthOptions={monthOptions}
          orders={orders}
          onDelete={handleDelete}
          onEdit={openEditForm}
          onFilterChange={setFilters}
          onSelect={handleSelectOrder}
          selectedOrderId={selectedOrder?.id || null}
        />
        <BeverageOrderDetail
          detailState={detailState}
          order={selectedOrder}
          onDelete={handleDelete}
          onEdit={openEditForm}
        />
      </section>
    </div>
  );
}

function BeverageOrderStats({ summary, isLoading, error }) {
  const cards = [
    { label: "전체 기록", value: Number(summary.total || 0).toLocaleString("ko-KR") },
    { label: "이번 달 기록", value: Number(summary.this_month || 0).toLocaleString("ko-KR") },
    { label: "음료", value: Number(summary.beverage || 0).toLocaleString("ko-KR") },
    { label: "소모품", value: Number(summary.supplies || 0).toLocaleString("ko-KR") },
    { label: "전체 금액", value: formatCurrency(summary.total_amount_total) },
    { label: "이번 달 금액", value: formatCurrency(summary.this_month_amount) },
  ];
  return (
    <section className="beverage-stats beverage-stats-compact">
      {cards.map((card) => (
        <article className="beverage-stat-card" key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
        </article>
      ))}
      {isLoading && <span className="status-pill">집계 중</span>}
      {error && <span className="lookup-warning">{error}</span>}
    </section>
  );
}

function BeverageOrderForm({
  editingOrder,
  expectedTitle,
  expectedMonth,
  form,
  previewUrl,
  submitState,
  onCancel,
  onChangeAmount,
  onChangeMemo,
  onChangeOrderType,
  onFileChange,
  onPaste,
  onSubmit,
}) {
  const currentImageUrl = editingOrder?.image_url ? getImageUrl(editingOrder.image_url) : "";
  return (
    <section className="quick-create beverage-image-form-panel" onPaste={onPaste}>
      <div className="quick-create-heading">
        <div>
          <h3>{editingOrder ? "게시글 수정" : "글쓰기"}</h3>
          <p>쿠팡 주문 캡처 이미지 1장만 첨부하거나 붙여넣습니다.</p>
        </div>
      </div>
      <form className="beverage-image-form" onSubmit={onSubmit}>
        <div className="beverage-auto-preview">
          <span>자동 제목</span>
          <strong>{editingOrder?.title || expectedTitle}</strong>
          <small>주문월: {editingOrder?.order_month || expectedMonth}</small>
        </div>
        <label className="field beverage-file-field">
          <span>{editingOrder ? "이미지 교체" : "이미지 첨부"}</span>
          <input
            accept="image/jpeg,image/png,image/webp"
            type="file"
            onChange={(event) => onFileChange(event.target.files?.[0])}
          />
        </label>
        <label className="field beverage-type-field">
          <span>구분</span>
          <select
            value={normalizeOrderType(form.order_type)}
            onChange={(event) => onChangeOrderType(event.target.value)}
          >
            {BEVERAGE_ORDER_TYPES.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="field beverage-amount-field">
          <span>총 결제금액</span>
          <input
            min="0"
            placeholder="예: 58300"
            type="number"
            value={form.total_amount}
            onChange={(event) => onChangeAmount(event.target.value)}
          />
        </label>
        <label className="field beverage-image-memo-field">
          <span>메모</span>
          <textarea
            rows="3"
            value={form.memo}
            onChange={(event) => onChangeMemo(event.target.value)}
            placeholder="필요한 경우에만 입력합니다."
          />
        </label>
        <div className="beverage-image-preview">
          {previewUrl ? (
            <img src={previewUrl} alt="선택한 이미지 미리보기" />
          ) : currentImageUrl ? (
            <img src={currentImageUrl} alt="현재 등록된 이미지" />
          ) : (
            <span>이미지를 선택하거나 Ctrl+V로 붙여넣어주세요.</span>
          )}
        </div>
        <div className="quick-create-actions">
          {submitState.error && <span className="inline-alert">{submitState.error}</span>}
          <button type="button" className="secondary-button" onClick={onCancel}>
            취소
          </button>
          <button type="submit" className="primary-action" disabled={submitState.isSubmitting}>
            {submitState.isSubmitting ? "저장 중..." : editingOrder ? "수정 저장" : "저장"}
          </button>
        </div>
      </form>
    </section>
  );
}

function BeverageOrderList({
  orders,
  isLoading,
  error,
  filters,
  monthOptions,
  selectedOrderId,
  editingOrderId,
  onFilterChange,
  onSelect,
  onEdit,
  onDelete,
}) {
  const safeOrders = Array.isArray(orders) ? orders : [];
  return (
    <section className="content-panel beverage-list-panel">
      <div className="section-heading">
        <div>
          <h2>게시글 목록</h2>
          <p>주문월과 검색어로 캡처 게시글을 찾습니다.</p>
        </div>
      </div>

      <div className="beverage-list-controls beverage-board-controls">
        <label className="field">
          <span>구분</span>
          <select
            value={filters.order_type}
            onChange={(event) => onFilterChange({ ...filters, order_type: event.target.value })}
          >
            <option value="">전체</option>
            {BEVERAGE_ORDER_TYPES.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>주문월</span>
          <select
            value={filters.order_month}
            onChange={(event) => onFilterChange({ ...filters, order_month: event.target.value })}
          >
            <option value="">전체</option>
            {monthOptions.map((month) => (
              <option key={month} value={month}>{month}</option>
            ))}
          </select>
        </label>
        <label className="field beverage-search-field">
          <span>검색</span>
          <input
            value={filters.keyword}
            onChange={(event) => onFilterChange({ ...filters, keyword: event.target.value })}
            placeholder="제목, 메모, 파일명"
          />
        </label>
      </div>

      {isLoading ? (
        <div className="state-panel">음료 주문 기록을 불러오는 중입니다.</div>
      ) : error ? (
        <div className="state-panel state-error">
          <strong>음료 주문 기록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      ) : safeOrders.length === 0 ? (
        <div className="state-panel">
          <strong>등록된 음료 주문 캡처가 없습니다.</strong>
          <span>글쓰기 버튼으로 첫 캡처 이미지를 추가해주세요.</span>
        </div>
      ) : (
        <div className="beverage-post-list">
          {safeOrders.map((order) => (
            <article
              className={[
                "beverage-post-item",
                "beverage-board-item",
                selectedOrderId === order.id ? "selected" : "",
                editingOrderId === order.id ? "editing" : "",
              ].filter(Boolean).join(" ")}
              key={order.id}
            >
              <button type="button" className="beverage-thumbnail-button" onClick={() => onSelect(order)}>
                {order.image_url ? (
                  <img src={getImageUrl(order.image_url)} alt={`${order.title} 미리보기`} />
                ) : (
                  <span>이미지 없음</span>
                )}
              </button>
              <button type="button" className="beverage-post-main" onClick={() => onSelect(order)}>
                <span className="beverage-post-meta-line">
                  <OrderTypeBadge orderType={order.order_type} />
                  <span className="beverage-post-date">{formatText(order.order_month)}</span>
                </span>
                <strong>{order.title}</strong>
                <span>{formatDateTime(order.created_at)}</span>
                {order.memo && <small>{truncateText(order.memo, 70)}</small>}
              </button>
              <div className="beverage-post-amount">
                <span>총 결제금액</span>
                <strong>{formatCurrency(order.total_amount)}</strong>
              </div>
              <div className="software-row-actions beverage-actions">
                <button type="button" className="secondary-button software-action-button" onClick={() => onEdit(order)}>
                  수정
                </button>
                <button type="button" className="danger-button software-action-button" onClick={() => onDelete(order)}>
                  삭제
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function BeverageOrderDetail({ order, detailState, onEdit, onDelete }) {
  return (
    <aside className="content-panel beverage-detail-panel">
      <div className="section-heading">
        <div>
          <h2>상세 보기</h2>
          <p>선택한 캡처 이미지를 크게 확인합니다.</p>
        </div>
      </div>
      {detailState.isLoading ? (
        <div className="state-panel">상세 내용을 불러오는 중입니다.</div>
      ) : detailState.error ? (
        <div className="state-panel state-error">
          <strong>상세 내용을 불러오지 못했습니다.</strong>
          <span className="state-detail">{detailState.error}</span>
        </div>
      ) : !order ? (
        <div className="state-panel">목록에서 게시글을 선택해주세요.</div>
      ) : (
        <div className="beverage-detail-body">
          <div className="beverage-detail-title">
            <span className="beverage-detail-meta">
              <OrderTypeBadge orderType={order.order_type} />
              <span>{formatText(order.order_month)}</span>
            </span>
            <h3>{order.title}</h3>
          </div>
          {order.image_url && (
            <a href={getImageUrl(order.image_url)} target="_blank" rel="noreferrer" className="beverage-detail-image-link">
              <img className="beverage-detail-image" src={getImageUrl(order.image_url)} alt={order.title} />
            </a>
          )}
          <InfoRow label="총 결제금액" value={formatCurrency(order.total_amount)} />
          <InfoRow label="원본 파일명" value={formatText(order.image_original_name)} />
          <InfoRow label="메모" value={formatText(order.memo)} />
          <InfoRow label="등록일" value={formatDateTime(order.created_at)} />
          <InfoRow label="수정일" value={formatDateTime(order.updated_at)} />
          <div className="software-row-actions beverage-detail-actions">
            <button type="button" className="secondary-button software-action-button" onClick={() => onEdit(order)}>
              수정
            </button>
            <button type="button" className="danger-button software-action-button" onClick={() => onDelete(order)}>
              삭제
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="beverage-info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function OrderTypeBadge({ orderType }) {
  const normalizedType = normalizeOrderType(orderType);
  return (
    <span className={`beverage-type-badge beverage-type-${normalizedType}`}>
      {getOrderTypeLabel(normalizedType)}
    </span>
  );
}

function getImageUrl(value) {
  if (!value) {
    return "";
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }
  return `${API_BASE_URL}${value}`;
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function normalizeOrderType(value) {
  return value === "supplies" ? "supplies" : "beverage";
}

function getOrderTypeLabel(value) {
  return normalizeOrderType(value) === "supplies" ? "소모품" : "음료";
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

function formatCurrency(value) {
  if (value === null || value === undefined || value === "" || Number(value) === 0) {
    return "-";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }
  return `₩${numericValue.toLocaleString("ko-KR")}`;
}

function truncateText(value, maxLength) {
  const text = String(value || "");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}...`;
}

export default BeverageOrderPage;
