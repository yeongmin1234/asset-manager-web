import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  createBeverageOrder,
  deleteBeverageOrder,
  getBeverageOrder,
  getBeverageOrderSummary,
  getBeverageOrders,
  updateBeverageOrder,
} from "../api/client.js";

const INITIAL_FORM = {
  order_date: "",
  order_month: "",
  vendor: "쿠팡",
  title: "",
  items_summary: "",
  total_amount: "",
  quantity_summary: "",
  requester: "",
  payment_method: "법인카드",
  order_url: "",
  memo: "",
};

const INITIAL_FILTERS = {
  order_month: "",
  vendor: "",
  keyword: "",
};

const INITIAL_SUMMARY = {
  total: 0,
  this_month: 0,
  total_amount: 0,
  this_month_amount: 0,
};

const VENDOR_OPTIONS = ["쿠팡", "이마트", "기타"];
const PAYMENT_OPTIONS = ["법인카드", "개인카드", "기타"];

function BeverageOrderPage() {
  const [orders, setOrders] = useState([]);
  const [summary, setSummary] = useState(INITIAL_SUMMARY);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [form, setForm] = useState(INITIAL_FORM);
  const [editingOrder, setEditingOrder] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
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
    if (!editingOrder) {
      setForm(INITIAL_FORM);
      setSubmitState({ isSubmitting: false, message: "", error: "" });
      return;
    }

    setForm({
      order_date: editingOrder.order_date || "",
      order_month: editingOrder.order_month || "",
      vendor: editingOrder.vendor || "쿠팡",
      title: editingOrder.title || "",
      items_summary: editingOrder.items_summary || "",
      total_amount: String(editingOrder.total_amount ?? ""),
      quantity_summary: editingOrder.quantity_summary || "",
      requester: editingOrder.requester || "",
      payment_method: editingOrder.payment_method || "법인카드",
      order_url: editingOrder.order_url || "",
      memo: editingOrder.memo || "",
    });
    setSubmitState({ isSubmitting: false, message: "", error: "" });
  }, [editingOrder]);

  const orderMonthOptions = useMemo(() => {
    const values = new Set();
    orders.forEach((order) => {
      if (order.order_month) {
        values.add(order.order_month);
      }
    });
    if (form.order_month) {
      values.add(form.order_month);
    }
    return Array.from(values).sort().reverse();
  }, [form.order_month, orders]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "order_date" && value ? { order_month: value.slice(0, 7) } : {}),
    }));
    setSubmitState((current) => ({ ...current, message: "", error: "" }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.title.trim()) {
      setSubmitState({ isSubmitting: false, message: "", error: "제목을 입력해주세요." });
      return;
    }

    setSubmitState({ isSubmitting: true, message: "", error: "" });
    try {
      const payload = buildPayload(form);
      if (editingOrder) {
        const updated = await updateBeverageOrder(editingOrder.id, payload);
        setEditingOrder(null);
        setSelectedOrder(updated);
        setSubmitState({ isSubmitting: false, message: "음료 주문 기록을 수정했습니다.", error: "" });
      } else {
        const created = await createBeverageOrder(payload);
        setForm(INITIAL_FORM);
        setSelectedOrder(created);
        setSubmitState({ isSubmitting: false, message: "음료 주문 기록을 등록했습니다.", error: "" });
      }
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
    const confirmed = window.confirm(`${order.title || "선택한 음료 주문 기록"}을 삭제할까요?`);
    if (!confirmed) {
      return;
    }
    await deleteBeverageOrder(order.id);
    if (editingOrder?.id === order.id) {
      setEditingOrder(null);
    }
    if (selectedOrder?.id === order.id) {
      setSelectedOrder(null);
    }
    await Promise.all([loadOrders(), loadSummary()]);
  };

  const handleEdit = (order) => {
    setEditingOrder(order);
    setSelectedOrder(order);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="beverage-page">
      <div className="portal-screen-heading beverage-heading">
        <div>
          <h2>음료주문기록</h2>
          <p>쿠팡 등에서 주문한 사내 음료 구매 내역을 게시글 형식으로 관리합니다.</p>
        </div>
      </div>

      <BeverageOrderStats
        error={summaryState.error}
        isLoading={summaryState.isLoading}
        summary={summary}
      />

      <section className="quick-create beverage-form-panel">
        <div className="quick-create-heading">
          <div>
            <h3>{editingOrder ? "음료 주문 기록 수정" : "게시글 등록"}</h3>
            <p>주문 내역은 직접 입력하며, 쿠팡 로그인이나 외부 연동은 하지 않습니다.</p>
          </div>
        </div>
        <form className="beverage-form" onSubmit={handleSubmit}>
          <Field name="order_date" label="주문일" type="date" value={form.order_date} onChange={handleChange} />
          <Field name="order_month" label="주문월" type="month" value={form.order_month} onChange={handleChange} />
          <label className="field">
            <span>구매처</span>
            <select name="vendor" value={form.vendor} onChange={handleChange}>
              {VENDOR_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <Field name="title" label="제목" required value={form.title} onChange={handleChange} />
          <Field name="items_summary" label="주문 품목" value={form.items_summary} onChange={handleChange} />
          <Field name="quantity_summary" label="수량" value={form.quantity_summary} onChange={handleChange} />
          <Field name="total_amount" label="총 금액" type="number" min="0" value={form.total_amount} onChange={handleChange} />
          <Field name="requester" label="요청자/등록자" value={form.requester} onChange={handleChange} />
          <label className="field">
            <span>결제수단</span>
            <select name="payment_method" value={form.payment_method} onChange={handleChange}>
              {PAYMENT_OPTIONS.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <Field name="order_url" label="주문 링크" type="url" value={form.order_url} onChange={handleChange} />
          <label className="field beverage-memo-field">
            <span>메모</span>
            <textarea name="memo" rows="3" value={form.memo} onChange={handleChange} />
          </label>
          <div className="quick-create-actions">
            {submitState.message && <span className="inline-success">{submitState.message}</span>}
            {submitState.error && <span className="inline-alert">{submitState.error}</span>}
            {editingOrder && (
              <button type="button" className="secondary-button" onClick={() => setEditingOrder(null)}>
                수정 취소
              </button>
            )}
            <button type="submit" className="primary-action" disabled={submitState.isSubmitting}>
              {submitState.isSubmitting ? "저장 중..." : editingOrder ? "수정 저장" : "저장"}
            </button>
          </div>
        </form>
      </section>

      <section className="beverage-content-grid">
        <BeverageOrderList
          editingOrderId={editingOrder?.id || null}
          error={listState.error}
          filters={filters}
          isLoading={listState.isLoading}
          monthOptions={orderMonthOptions}
          orders={orders}
          onDelete={handleDelete}
          onEdit={handleEdit}
          onFilterChange={setFilters}
          onSelect={handleSelectOrder}
          selectedOrderId={selectedOrder?.id || null}
        />
        <BeverageOrderDetail
          detailState={detailState}
          order={selectedOrder}
          onDelete={handleDelete}
          onEdit={handleEdit}
        />
      </section>
    </div>
  );
}

function BeverageOrderStats({ summary, isLoading, error }) {
  const cards = [
    { label: "전체 기록", value: Number(summary.total || 0).toLocaleString("ko-KR") },
    { label: "이번 달 주문", value: Number(summary.this_month || 0).toLocaleString("ko-KR") },
    { label: "전체 금액", value: formatCurrency(summary.total_amount) },
    { label: "이번 달 금액", value: formatCurrency(summary.this_month_amount) },
  ];
  return (
    <section className="beverage-stats">
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
          <h2>주문 목록</h2>
          <p>주문월, 구매처, 검색어로 음료 주문 기록을 찾습니다.</p>
        </div>
      </div>

      <div className="beverage-list-controls">
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
        <label className="field">
          <span>구매처</span>
          <select
            value={filters.vendor}
            onChange={(event) => onFilterChange({ ...filters, vendor: event.target.value })}
          >
            <option value="">전체</option>
            {VENDOR_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label className="field beverage-search-field">
          <span>검색</span>
          <input
            value={filters.keyword}
            onChange={(event) => onFilterChange({ ...filters, keyword: event.target.value })}
            placeholder="제목, 품목, 요청자, 메모"
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
          <strong>등록된 음료 주문 기록이 없습니다.</strong>
          <span>게시글 등록 폼으로 첫 기록을 추가해주세요.</span>
        </div>
      ) : (
        <div className="beverage-post-list">
          {safeOrders.map((order) => (
            <article
              className={[
                "beverage-post-item",
                selectedOrderId === order.id ? "selected" : "",
                editingOrderId === order.id ? "editing" : "",
              ].filter(Boolean).join(" ")}
              key={order.id}
            >
              <button type="button" className="beverage-post-main" onClick={() => onSelect(order)}>
                <span className="beverage-post-date">{formatDate(order.order_date)}</span>
                <strong>{order.title}</strong>
                <span>{formatText(order.items_summary)}</span>
                {order.memo && <small>{truncateText(order.memo, 80)}</small>}
              </button>
              <div className="beverage-post-meta">
                <span>{formatText(order.vendor)}</span>
                <span>{formatCurrency(order.total_amount)}</span>
                <span>{formatText(order.requester)}</span>
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
          <p>선택한 주문 기록의 전체 내용을 확인합니다.</p>
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
        <div className="state-panel">목록에서 주문 기록을 선택해주세요.</div>
      ) : (
        <div className="beverage-detail-body">
          <div className="beverage-detail-title">
            <span>{formatText(order.order_month)}</span>
            <h3>{order.title}</h3>
          </div>
          <InfoRow label="주문일" value={formatDate(order.order_date)} />
          <InfoRow label="구매처" value={formatText(order.vendor)} />
          <InfoRow label="주문 품목" value={formatText(order.items_summary)} />
          <InfoRow label="수량" value={formatText(order.quantity_summary)} />
          <InfoRow label="총 금액" value={formatCurrency(order.total_amount)} />
          <InfoRow label="요청자/등록자" value={formatText(order.requester)} />
          <InfoRow label="결제수단" value={formatText(order.payment_method)} />
          <InfoRow label="메모" value={formatText(order.memo)} />
          <InfoRow label="등록일" value={formatDateTime(order.created_at)} />
          <InfoRow label="수정일" value={formatDateTime(order.updated_at)} />
          {order.order_url && (
            <a className="primary-action beverage-link-button" href={order.order_url} target="_blank" rel="noreferrer">
              주문 링크 열기
            </a>
          )}
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

function Field({ label, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
    </label>
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

function buildPayload(form) {
  return {
    order_date: form.order_date || null,
    order_month: textOrNull(form.order_month || (form.order_date ? form.order_date.slice(0, 7) : "")),
    vendor: textOrNull(form.vendor),
    title: form.title.trim(),
    items_summary: textOrNull(form.items_summary),
    total_amount: numberOrNull(form.total_amount),
    quantity_summary: textOrNull(form.quantity_summary),
    requester: textOrNull(form.requester),
    payment_method: textOrNull(form.payment_method),
    order_url: textOrNull(form.order_url),
    memo: textOrNull(form.memo),
  };
}

function textOrNull(value) {
  const trimmedValue = String(value || "").trim();
  return trimmedValue || null;
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatDate(value) {
  return value || "-";
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
  if (value === null || value === undefined || value === "") {
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
