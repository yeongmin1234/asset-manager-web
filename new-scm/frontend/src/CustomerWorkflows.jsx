import React, { useEffect, useState } from "react";

const PAGE_SIZE = 20;
export const consultationMock = [];
export const returnMock = [];
export const exchangeMock = [];
export const asMock = [];
export const saleMock = [];

export function WorkflowModal({ title, children, onClose, onSubmit, submitLabel }) {
  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div className="workflow-modal-layer">
      <section className="workflow-modal" role="dialog" aria-modal="true" aria-label={title}>
        <header><h2>{title}</h2><button type="button" onClick={onClose}>닫기</button></header>
        <form onSubmit={onSubmit} noValidate>
          {children}
          <footer><button type="button" onClick={onClose}>취소</button><button type="submit" className="primary">{submitLabel}</button></footer>
        </form>
      </section>
    </div>
  );
}

function Field({ label, required, error, children, wide }) {
  return <label className={`workflow-field${wide ? " workflow-field--wide" : ""}`}><span>{required && <em>*</em>}{label}</span>{children}{error && <small>{error}</small>}</label>;
}

const asEmpty = { customer: "", phone: "", mobile: "", address: "", brand: "", product: "", serial: "", purchaseDate: "", market: "", pickupNo: "", pickupDate: "", pickupInvoice: "", symptom: "", memo: "" };

export function AsCreateModal({ onClose, onCreate }) {
  const [form, setForm] = useState(asEmpty);
  const [errors, setErrors] = useState({});
  const update = (key, value) => { setForm((current) => ({ ...current, [key]: value })); setErrors((current) => ({ ...current, [key]: "" })); };
  const submit = (event) => {
    event.preventDefault();
    const next = {};
    [["customer", "고객명"], ["mobile", "핸드폰"], ["brand", "브랜드"], ["product", "상품명"], ["symptom", "증상 요약"]].forEach(([key, label]) => { if (!form[key].trim()) next[key] = `${label}을 입력해 주세요.`; });
    setErrors(next);
    if (Object.keys(next).length) return;
    onCreate({ id: `AS-TEMP-${form.serial || "001"}`, no: 1001, changed: "2026-07-27 15:10", date: "2026-07-27 15:10", status: "AS접수", manager: "현재사용자", product: form.product, serial: form.serial || "-", symptom: form.symptom, customer: form.customer, contact: form.mobile, inbound: "-", outbound: "-", pickup: `${form.pickupNo || "-"} (${form.pickupDate || "-"})` });
  };
  const input = (key, type = "text") => <input type={type} value={form[key]} onChange={(event) => update(key, event.target.value)} />;
  return <WorkflowModal title="AS 신규 접수 화면" onClose={onClose} onSubmit={submit} submitLabel="신규 AS건 작성 완료">
    <div className="workflow-modal-grid">
      <div>
        <h3>AS 고객정보 입력 <small>판매이력이 검색되지 않을 경우 직접 입력</small></h3>
        <div className="workflow-fields">
          <Field label="고객명" required error={errors.customer}>{input("customer")}</Field><Field label="전화">{input("phone")}</Field>
          <Field label="핸드폰" required error={errors.mobile}>{input("mobile")}</Field><Field label="주소">{input("address")}</Field>
        </div>
        <h3>제품정보 입력 <small>판매이력이 검색되지 않을 경우 직접 입력</small></h3>
        <div className="workflow-fields">
          <Field label="브랜드" required error={errors.brand}><select value={form.brand} onChange={(event) => update("brand", event.target.value)}><option value="">선택</option><option>Balmuda</option><option>Vermicular</option><option>Moon</option><option>기타</option></select></Field>
          <Field label="상품명/상품분류" required error={errors.product}>{input("product")}</Field><Field label="S/N">{input("serial")}</Field>
          <Field label="고객구매일">{input("purchaseDate", "date")}</Field><Field label="구매마켓명">{input("market")}</Field>
        </div>
        <h3>집하예약정보 입력</h3>
        <div className="workflow-fields">
          <Field label="집하예약번호">{input("pickupNo")}</Field><Field label="집하요청일">{input("pickupDate", "date")}</Field><Field label="집하송장번호">{input("pickupInvoice")}</Field>
        </div>
      </div>
      <div>
        <h3>AS 접수 내용</h3>
        <div className="workflow-fields workflow-fields--single">
          <Field label="증상 요약" required error={errors.symptom}><input maxLength="30" value={form.symptom} placeholder="증상을 키워드 중심으로 작성(최대30자)" onChange={(event) => update("symptom", event.target.value)} /><b>{form.symptom.length}/30</b></Field>
          <Field label="AS 상담 메모"><textarea value={form.memo} placeholder="AS 접수시 제품 및 고객 특이사항을 메모 하십시오" onChange={(event) => update("memo", event.target.value)} /></Field>
        </div>
      </div>
    </div>
  </WorkflowModal>;
}

const saleEmpty = { market: "", orderNo: "", orderer: "", orderPhone: "", orderMobile: "", recipient: "", recipientPhone: "", recipientMobile: "", zip: "", address: "", deliveryMessage: "", brand: "", category: "", product: "", quantity: "1", revenue: "0", salePrice: "0", promiseDate: "", memo: "" };

export function SaleCreateModal({ onClose, onCreate }) {
  const [form, setForm] = useState(saleEmpty);
  const [errors, setErrors] = useState({});
  const update = (key, value) => { setForm((current) => ({ ...current, [key]: value })); setErrors((current) => ({ ...current, [key]: "" })); };
  const copyOrderer = () => setForm((current) => ({ ...current, recipient: current.orderer, recipientPhone: current.orderPhone, recipientMobile: current.orderMobile }));
  const submit = (event) => {
    event.preventDefault();
    const next = {};
    [["orderer", "주문자"], ["recipient", "수취인"], ["brand", "브랜드"], ["product", "상품명"]].forEach(([key, label]) => { if (!form[key].trim()) next[key] = `${label}을 입력해 주세요.`; });
    if (Number(form.quantity) < 1) next.quantity = "수량은 1 이상이어야 합니다.";
    if (Number(form.revenue) < 0 || Number(form.salePrice) < 0) next.revenue = "금액은 0 이상이어야 합니다.";
    setErrors(next);
    if (Object.keys(next).length) return;
    onCreate({ ...form, id: `SALE-TEMP-${form.orderNo || "001"}`, date: "2026-07-27 15:20", status: "판매접수" });
  };
  const input = (key, type = "text") => <input type={type} value={form[key]} onChange={(event) => update(key, event.target.value)} />;
  return <WorkflowModal title="판매 데이터 수기 등록" onClose={onClose} onSubmit={submit} submitLabel="판매 데이터 입력">
    <div className="workflow-modal-grid">
      <div>
        <h3>주문정보</h3><div className="workflow-fields"><Field label="마켓명"><select value={form.market} onChange={(event) => update("market", event.target.value)}><option value="">선택</option><option>온라인몰</option><option>롯데백화점</option><option>신세계백화점</option></select></Field><Field label="주문번호">{input("orderNo")}</Field></div>
        <h3>주문하시는 분 정보</h3><div className="workflow-fields"><Field label="주문자" required error={errors.orderer}>{input("orderer")}</Field><Field label="전화번호">{input("orderPhone")}</Field><Field label="핸드폰">{input("orderMobile")}</Field></div>
        <h3>받으시는 분 정보 <button type="button" onClick={copyOrderer}>주문자 동일</button></h3><div className="workflow-fields"><Field label="수취인" required error={errors.recipient}>{input("recipient")}</Field><Field label="전화번호">{input("recipientPhone")}</Field><Field label="핸드폰">{input("recipientMobile")}</Field><Field label="우편번호">{input("zip")}</Field><Field label="주소" wide>{input("address")}</Field><Field label="배송메시지" wide>{input("deliveryMessage")}</Field></div>
      </div>
      <div>
        <h3>주문 제품 정보</h3><div className="workflow-fields">
          <Field label="브랜드" required error={errors.brand}><select value={form.brand} onChange={(event) => update("brand", event.target.value)}><option value="">선택</option><option>Balmuda</option><option>Vermicular</option><option>Moon</option><option>기타</option></select></Field>
          <Field label="상품구분">{input("category")}</Field><Field label="상품명" required error={errors.product}>{input("product")}</Field>
          <Field label="수량" required error={errors.quantity}>{input("quantity", "number")}</Field><Field label="매출액" error={errors.revenue}>{input("revenue", "number")}</Field>
          <Field label="판매가">{input("salePrice", "number")}</Field><Field label="고객약속일">{input("promiseDate", "date")}</Field>
          <Field label="판매 메모" wide><textarea value={form.memo} onChange={(event) => update("memo", event.target.value)} /></Field>
        </div>
      </div>
    </div>
  </WorkflowModal>;
}

export function Pagination({ page, onPage }) {
  return <nav className="workflow-pagination" aria-label="페이지 이동"><button type="button" disabled={page === 1} onClick={() => onPage(page - 1)}>이전</button>{Array.from({ length: 30 }, (_, index) => index + 1).map((number) => <button type="button" key={number} className={page === number ? "active" : ""} onClick={() => onPage(number)}>{number}</button>)}<button type="button" disabled={page === 30} onClick={() => onPage(page + 1)}>다음</button></nav>;
}

export function StatusTabs({ statuses, active, rows, onChange, countLabels = {} }) {
  return <div className="workflow-status-tabs">{statuses.map((status) => <button type="button" key={status} className={active === status ? "active" : ""} onClick={() => onChange(status)}>{status}<span>{countLabels[status] ?? (status === "전체" ? rows.length : rows.filter((row) => row.status === status).length)}건</span></button>)}</div>;
}

function WorkflowList({ title, statuses, rows, columns, selectable = false, countLabels }) {
  const [activeStatus, setActiveStatus] = useState("전체");
  const [page, setPage] = useState(1);
  const [checked, setChecked] = useState(() => new Set());
  const [selected, setSelected] = useState(null);
  const filtered = activeStatus === "전체" ? rows : rows.filter((row) => row.status === activeStatus);
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const allPageChecked = pageRows.length > 0 && pageRows.every((row) => checked.has(row.id));
  const changeStatus = (status) => { setActiveStatus(status); setPage(1); };
  const toggleAll = () => setChecked((current) => { const next = new Set(current); pageRows.forEach((row) => allPageChecked ? next.delete(row.id) : next.add(row.id)); return next; });
  const toggleOne = (id) => setChecked((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; });
  return <section className="workflow-list-page">
    <header><div><p>CUSTOMER WORKFLOW</p><h2>{title}</h2></div>{selectable && <span>{checked.size}건 선택</span>}</header>
    <StatusTabs statuses={statuses} active={activeStatus} rows={rows} onChange={changeStatus} countLabels={countLabels} />
    <div className="workflow-table-wrap"><table className="workflow-table"><thead><tr>{selectable && <th><input type="checkbox" checked={allPageChecked} onChange={toggleAll} /></th>}{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{pageRows.map((row) => <tr key={row.id} className={selected === row.id ? "selected" : ""} onClick={() => setSelected(row.id)}>{selectable && <td><input type="checkbox" checked={checked.has(row.id)} onChange={() => toggleOne(row.id)} onClick={(event) => event.stopPropagation()} /></td>}{columns.map((column) => { const value = column.render ? column.render(row[column.key], row) : row[column.key]; return <td key={column.key} className={column.left ? "text-left" : ""} title={String(value ?? "")}>{column.status ? <span className={`workflow-badge workflow-badge--${row.status}`}>{value}</span> : value}</td>; })}</tr>)}</tbody></table></div>
    <Pagination page={page} onPage={setPage} />
  </section>;
}

export function ConsultationList() {
  const columns = [{ key: "no", label: "No." }, { key: "date", label: "접수일시" }, { key: "status", label: "상태", status: true }, { key: "manager", label: "담당자" }, { key: "interest", label: "관심제품", left: true }, { key: "customer", label: "고객명" }, { key: "contact", label: "연락처" }, { key: "region", label: "주소(지역)", left: true }, { key: "detail", label: "상담내역(최근 1건)", left: true }];
  return <WorkflowList title="상담목록" statuses={["전체", "상담접수", "회신준비", "상담완료"]} rows={consultationMock} columns={columns} selectable countLabels={{ 상담접수: 0, 회신준비: 0, 상담완료: 0 }} />;
}

export function ReturnList() {
  const columns = [{ key: "no", label: "No." }, { key: "date", label: "등록일시" }, { key: "status", label: "상태", status: true }, { key: "product", label: "상품명", left: true }, { key: "customer", label: "고객명" }, { key: "contact", label: "연락처" }, { key: "inbound", label: "입고일" }, { key: "returnInvoice", label: "반품송장번호" }, { key: "pickupNo", label: "집하예약번호" }, { key: "pickupDate", label: "집하요청일" }];
  return <WorkflowList title="반품목록" statuses={["전체", "반품진행", "반품완료"]} rows={returnMock} columns={columns} />;
}

export function ExchangeList() {
  const columns = [{ key: "no", label: "No." }, { key: "date", label: "등록일시" }, { key: "status", label: "상태", status: true }, { key: "product", label: "상품명", left: true }, { key: "orderer", label: "주문인(연락처)", left: true }, { key: "recipient", label: "수취인(연락처)", left: true }, { key: "inbound", label: "입고일" }, { key: "inboundInvoice", label: "입고송장" }, { key: "outbound", label: "출고일" }, { key: "outboundInvoice", label: "출고송장" }, { key: "pickupNo", label: "집하예약번호" }, { key: "pickupDate", label: "집하요청일" }];
  return <WorkflowList title="교환목록" statuses={["전체", "교환진행", "교환완료"]} rows={exchangeMock} columns={columns} />;
}

export function AsList({ rows }) {
  const columns = [{ key: "no", label: "No." }, { key: "changed", label: "최종변경" }, { key: "status", label: "상태", status: true }, { key: "manager", label: "담당자" }, { key: "product", label: "상품명", left: true }, { key: "serial", label: "S/N" }, { key: "symptom", label: "증상", left: true }, { key: "customer", label: "고객명" }, { key: "contact", label: "연락처" }, { key: "inbound", label: "입고일(입고송장)" }, { key: "outbound", label: "출고일(출고송장)" }, { key: "pickup", label: "집하예약번호(집하요청일)" }];
  return <WorkflowList title="AS목록" statuses={["전체", "AS접수", "입고대기", "AS입고대기", "회의용", "수리중", "AS중단", "AS완료"]} rows={rows} columns={columns} selectable />;
}

export function SaleList({ rows }) {
  const columns = [{ key: "no", label: "No." }, { key: "date", label: "등록일시" }, { key: "status", label: "상태", status: true }, { key: "market", label: "마켓명" }, { key: "orderNo", label: "주문번호" }, { key: "brand", label: "브랜드" }, { key: "product", label: "상품명", left: true }, { key: "quantity", label: "수량" }, { key: "revenue", label: "매출액", render: (value) => Number(value).toLocaleString("ko-KR") }, { key: "orderer", label: "주문자" }, { key: "recipient", label: "수취인" }];
  return <WorkflowList title="판매목록" statuses={["전체", "판매접수", "판매완료"]} rows={rows} columns={columns} />;
}
