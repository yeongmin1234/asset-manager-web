import React, { useState } from "react";
import {
  AsCreateModal,
  AsList,
  ExchangeList,
  ReturnList,
  SaleCreateModal,
  SaleList,
  asMock,
  saleMock,
} from "./CustomerWorkflows";
import { InOutList, InOutManagement } from "./InOutWorkflows";
import ConsultationList from "./ConsultationList";

const workTabs = [
  { label: "AS접수", path: "/customer-consulting/as-reception" },
  { label: "판매접수", path: "/customer-consulting/sales-reception" },
  { label: "상담목록", path: "/customer-consulting/consultation-list" },
  { label: "반품목록", path: "/customer-consulting/return-list" },
  { label: "교환목록", path: "/customer-consulting/exchange-list" },
  { label: "AS목록", path: "/customer-consulting/as-list" },
  { label: "판매목록", path: "/customer-consulting/sales-list" },
  { label: "입출고목록", path: "/customer-consulting/logistics-list" },
  { label: "입출고관리", path: "/customer-consulting/logistics-management" },
];

const customers = [];
const consultationSeed = [];
const salesHistory = [];
const asHistory = [];
const logisticsHistory = [];

const emptyForm = {
  customerId: null,
  name: "",
  mobile: "",
  phone: "",
  address: "",
  product: "",
  detail: "",
  status: "상담접수",
};

function HistoryTable({ title, columns, rows, emptyText = "검색/콜 대기중", onRowClick, selectedRowId }) {
  return (
    <section className="consult-history-section">
      <h3>{title}</h3>
      <div className="consult-table-wrap">
        <table className="consult-table">
          <thead>
            <tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((row) => (
              <tr
                key={row.id}
                className={selectedRowId === row.id ? "consult-table__selected" : ""}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column) => {
                  const value = column.format ? column.format(row[column.key], row) : row[column.key];
                  return (
                    <td key={column.key} className={column.className || ""} title={String(value ?? "")}>
                      {column.badge ? <span className={`consult-badge consult-badge--${column.badge(row[column.key])}`}>{value}</span> : value}
                    </td>
                  );
                })}
              </tr>
            )) : (
              <tr><td className="consult-table__empty" colSpan={columns.length}>{emptyText}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AsReception() {
  const [search, setSearch] = useState({ phone: "", name: "", serial: "" });
  const [hasSearched, setHasSearched] = useState(false);
  const [activeCustomer, setActiveCustomer] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [consultations, setConsultations] = useState(consultationSeed);
  const [selectedSalesId, setSelectedSalesId] = useState(null);
  const [toast, setToast] = useState("");

  const results = hasSearched ? customers.filter((customer) => {
    const phoneQuery = search.phone.replace(/\D/g, "");
    const customerPhones = `${customer.mobile}${customer.phone}`.replace(/\D/g, "");
    return (!phoneQuery || customerPhones.endsWith(phoneQuery) || customerPhones.includes(phoneQuery))
      && (!search.name.trim() || customer.name.includes(search.name.trim()))
      && (!search.serial.trim() || customer.serial.toLowerCase().includes(search.serial.trim().toLowerCase()));
  }) : [];

  const selectedConsultations = activeCustomer
    ? consultations.filter((item) => item.customerId === activeCustomer.id)
    : consultations.filter((item) => item.isNew);
  const selectedSales = activeCustomer ? salesHistory.filter((item) => item.customerId === activeCustomer.id) : [];
  const selectedAs = activeCustomer ? asHistory.filter((item) => item.customerId === activeCustomer.id) : [];
  const selectedLogistics = activeCustomer ? logisticsHistory.filter((item) => item.customerId === activeCustomer.id) : [];

  function copyCustomer(customer) {
    setActiveCustomer(customer);
    setForm({
      customerId: customer.id,
      name: customer.name,
      mobile: customer.mobile,
      phone: customer.phone,
      address: customer.address,
      product: customer.product,
      detail: "",
      status: "상담접수",
    });
    setErrors({});
  }

  function resetSearch() {
    setSearch({ phone: "", name: "", serial: "" });
    setHasSearched(false);
    setActiveCustomer(null);
  }

  function resetForm() {
    setForm(emptyForm);
    setErrors({});
  }

  function registerConsultation() {
    const nextErrors = {};
    if (!form.name.trim()) nextErrors.name = "고객명을 입력해 주세요.";
    if (!form.mobile.trim()) nextErrors.mobile = "휴대전화번호를 입력해 주세요.";
    if (!form.product) nextErrors.product = "상담제품을 선택해 주세요.";
    if (!form.detail.trim()) nextErrors.detail = "상담내역을 입력해 주세요.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    const customer = activeCustomer ?? {
      id: `temp-${form.mobile}`,
      name: form.name,
      mobile: form.mobile,
      phone: form.phone,
      address: form.address,
      region: form.address.split(" ").slice(0, 2).join(" "),
      product: form.product,
      brand: form.product.includes("토스터") || form.product.includes("팟") ? "Balmuda" : "기타",
    };
    setActiveCustomer(customer);
    setConsultations((current) => [{
      id: `TEMP-${current.length + 1}`,
      customerId: customer.id,
      received: "2026-07-27 14:30",
      status: form.status,
      manager: "현재사용자",
      brand: customer.brand,
      product: form.product,
      customer: form.name,
      contact: form.mobile,
      region: customer.region || form.address,
      detail: form.detail,
      isNew: true,
    }, ...current]);
    setToast("상담이력이 임시 등록되었습니다.");
    window.setTimeout(() => setToast(""), 2500);
  }

  const consultationColumns = [
    { key: "id", label: "No." }, { key: "received", label: "접수일시" },
    { key: "status", label: "상태", badge: (value) => value === "상담완료" ? "done" : value === "회신준비" ? "waiting" : "active" },
    { key: "manager", label: "담당자" }, { key: "brand", label: "브랜드" },
    { key: "product", label: "상품명", className: "text-left" }, { key: "customer", label: "고객명" },
    { key: "contact", label: "연락처" }, { key: "region", label: "주소(지역)", className: "text-left" },
    { key: "detail", label: "상담내역(최근 1건)", className: "text-left" },
  ];
  const salesColumns = [
    { key: "id", label: "No." }, { key: "date", label: "등록일시" },
    { key: "status", label: "상태", badge: () => "neutral" }, { key: "manager", label: "담당자" },
    { key: "brand", label: "브랜드" }, { key: "product", label: "상품명" }, { key: "market", label: "마켓명" },
    { key: "order", label: "주문번호" }, { key: "quantity", label: "수량" },
    { key: "amount", label: "매출액", format: (value) => Number(value).toLocaleString("ko-KR"), className: "number" },
    { key: "orderer", label: "주문자" }, { key: "recipient", label: "수취인" }, { key: "response", label: "고객응대" },
  ];
  const asColumns = [
    { key: "id", label: "No." }, { key: "changed", label: "최종변경" },
    { key: "status", label: "상태", badge: () => "active" }, { key: "manager", label: "담당자" },
    { key: "brand", label: "브랜드" }, { key: "product", label: "상품명" }, { key: "customer", label: "고객명" },
    { key: "contact", label: "연락처" }, { key: "serial", label: "S/N" }, { key: "symptom", label: "증상" },
    { key: "inbound", label: "입고일" }, { key: "outbound", label: "출고일" }, { key: "visit", label: "방문" },
    { key: "visitDate", label: "방문예정일" },
  ];
  const logisticsColumns = [
    { key: "date", label: "처리일시" }, { key: "type", label: "구분", badge: () => "neutral" },
    { key: "product", label: "제품명", className: "text-left" }, { key: "manager", label: "담당자" },
    { key: "address", label: "주소", className: "text-left" },
  ];

  return (
    <>
      <div className="consult-top-grid">
        <section className="consult-form-panel">
          <h2>고객정보 검색</h2>
          <p className="consult-guide">검색 결과의 업무번호(No.)를 클릭하면 고객정보를 상담작성 폼으로 복사합니다.</p>
          <div className="customer-search-form">
            <label><span>전화번호</span><input value={search.phone} placeholder="자동연동 불가시 수동 검색가능 (끝자리 검색 지원)" onChange={(event) => setSearch({ ...search, phone: event.target.value })} /></label>
            <label><span>고객명</span><input value={search.name} onChange={(event) => setSearch({ ...search, name: event.target.value })} /></label>
            <label><span>S/N</span><input value={search.serial} onChange={(event) => setSearch({ ...search, serial: event.target.value })} /></label>
            <div className="consult-actions"><button type="button" onClick={resetSearch}>초기화</button><button type="button" className="primary" onClick={() => setHasSearched(true)}>수동 검색</button></div>
          </div>
          <div className="customer-results">
            {hasSearched && !results.length ? <p>검색 결과가 없습니다.</p> : results.map((customer) => (
              <button type="button" key={customer.id} onClick={() => copyCustomer(customer)}>
                <strong>{customer.workNo}</strong><span>{customer.name}</span><span>{customer.mobile}</span><span>{customer.serial}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="consult-form-panel">
          <h2>상담작성</h2>
          <div className="consult-write-form">
            <label><span>고객명 *</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />{errors.name && <small>{errors.name}</small>}</label>
            <div className="consult-phone-row">
              <label><span>휴대전화번호 *</span><input value={form.mobile} onChange={(event) => setForm({ ...form, mobile: event.target.value })} />{errors.mobile && <small>{errors.mobile}</small>}</label>
              <label><span>일반전화번호</span><input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
            </div>
            <label><span>주소</span><input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} /></label>
            <label><span>상담제품 *</span><select value={form.product} onChange={(event) => setForm({ ...form, product: event.target.value })}><option value="">제품 선택</option>{["더 토스터 프로", "라이스팟 미니", "문 에어 서큘레이터", "더 팟", "프라이팬 24cm", "더 스피커"].map((product) => <option key={product}>{product}</option>)}</select>{errors.product && <small>{errors.product}</small>}</label>
            <label><span>상담내역 *</span><textarea value={form.detail} placeholder="고객 상담 내역을 기록하십시오" onChange={(event) => setForm({ ...form, detail: event.target.value })} />{errors.detail && <small>{errors.detail}</small>}</label>
            <fieldset><legend>상담상태</legend>{["상담접수", "회신준비", "상담완료"].map((status) => <label key={status}><input type="radio" name="consult-status" checked={form.status === status} onChange={() => setForm({ ...form, status })} />{status}</label>)}</fieldset>
            <div className="consult-actions"><button type="button" onClick={resetForm}>초기화</button><button type="button" className="primary" onClick={registerConsultation}>상담등록</button></div>
          </div>
        </section>
      </div>

      <HistoryTable title="상담이력" columns={consultationColumns} rows={selectedConsultations} onRowClick={(row) => {
        const customer = customers.find((item) => item.id === row.customerId);
        if (customer) copyCustomer(customer);
      }} />
      <HistoryTable
        title="판매/교환/반품이력"
        columns={salesColumns}
        rows={selectedSales}
        selectedRowId={selectedSalesId}
        onRowClick={(row) => setSelectedSalesId(row.id)}
      />
      <HistoryTable title="AS이력" columns={asColumns} rows={selectedAs} />
      <HistoryTable title="입출고이력" columns={logisticsColumns} rows={selectedLogistics} />
      {toast && <div className="product-toast" role="status">{toast}</div>}
    </>
  );
}

export default function CustomerConsulting({ currentPath, onNavigate }) {
  const activeTab = workTabs.find((tab) => tab.path === currentPath) ?? workTabs[0];
  const [isAsModalOpen, setIsAsModalOpen] = useState(currentPath === "/customer-consulting/as-reception");
  const [isSaleModalOpen, setIsSaleModalOpen] = useState(currentPath === "/customer-consulting/sales-reception");
  const [asRecords, setAsRecords] = useState(asMock);
  const [saleRecords, setSaleRecords] = useState(saleMock);
  const [workflowToast, setWorkflowToast] = useState("");

  function showWorkflowToast(message) {
    setWorkflowToast(message);
    window.setTimeout(() => setWorkflowToast(""), 2500);
  }

  function handleTabClick(event, tab) {
    if (tab.path === "/customer-consulting/as-reception") {
      onNavigate(event, tab.path);
      setIsAsModalOpen(true);
      return;
    }
    if (tab.path === "/customer-consulting/sales-reception") {
      onNavigate(event, tab.path);
      setIsSaleModalOpen(true);
      return;
    }
    onNavigate(event, tab.path);
  }

  function renderTabContent() {
    if (activeTab.path === "/customer-consulting/as-reception") return <AsReception />;
    if (activeTab.path === "/customer-consulting/sales-reception") return <SaleList rows={saleRecords} />;
    if (activeTab.path === "/customer-consulting/consultation-list") return <ConsultationList />;
    if (activeTab.path === "/customer-consulting/return-list") return <ReturnList />;
    if (activeTab.path === "/customer-consulting/exchange-list") return <ExchangeList />;
    if (activeTab.path === "/customer-consulting/as-list") return <AsList rows={asRecords} />;
    if (activeTab.path === "/customer-consulting/sales-list") return <SaleList rows={saleRecords} />;
    if (activeTab.path === "/customer-consulting/logistics-list") return <InOutList onClose={() => onNavigate({ preventDefault() {} }, "/customer-consulting")} />;
    if (activeTab.path === "/customer-consulting/logistics-management") return <InOutManagement onClose={() => onNavigate({ preventDefault() {} }, "/customer-consulting")} />;
    return <AsReception />;
  }

  return (
    <section className="customer-consulting-page" aria-labelledby="customer-consulting-title">
      <div className="consult-page-heading">
        <div><p>CUSTOMER CONSULTING</p><h1 id="customer-consulting-title">고객상담</h1></div>
        <span className="page-panel__status">프론트엔드 개발 모드</span>
      </div>
      <nav className="consult-work-tabs" aria-label="고객상담 업무 탭">
        {workTabs.map((tab) => (
          <a key={tab.path} href={`#${tab.path}`} className={activeTab.path === tab.path ? "active" : ""} onClick={(event) => handleTabClick(event, tab)}>{tab.label}</a>
        ))}
      </nav>
      {renderTabContent()}
      {isAsModalOpen && <AsCreateModal onClose={() => setIsAsModalOpen(false)} onCreate={(record) => {
        setAsRecords((current) => [record, ...current]);
        setIsAsModalOpen(false);
        showWorkflowToast("신규 AS건이 임시 등록되었습니다.");
      }} />}
      {isSaleModalOpen && <SaleCreateModal onClose={() => setIsSaleModalOpen(false)} onCreate={(record) => {
        setSaleRecords((current) => [record, ...current]);
        setIsSaleModalOpen(false);
        showWorkflowToast("판매 데이터가 임시 등록되었습니다.");
      }} />}
      {workflowToast && <div className="product-toast" role="status">{workflowToast}</div>}
    </section>
  );
}
