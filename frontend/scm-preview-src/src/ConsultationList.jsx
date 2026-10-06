import React, { useEffect, useMemo, useState } from "react";
import ConsultationCreateModal from "./ConsultationCreateModal";
import { initialConsultations, initialCountLabels } from "./consultationMockData";
import MaskedText from "./components/common/MaskedText";
import { StatusBadge } from "./components/common/CommonUI";
import { usePermission } from "./hooks/usePermission";

const PAGE_SIZE = 20;
const statuses = ["전체", "상담접수", "회신준비", "상담완료"];
const searchFields = { customer: "고객명", contact: "연락처", interest: "관심제품", manager: "담당자", detail: "상담내용" };

function Pagination({ page, onChange }) {
  return <nav className="consult-list-pagination" aria-label="페이지 이동"><button type="button" disabled={page === 1} onClick={() => onChange(page - 1)}>이전</button>{Array.from({ length: 30 }, (_, index) => index + 1).map((number) => <button type="button" key={number} className={page === number ? "active" : ""} onClick={() => onChange(number)}>{number}</button>)}<button type="button" disabled={page === 30} onClick={() => onChange(page + 1)}>다음</button></nav>;
}

export default function ConsultationList() {
  const canCreate = usePermission("create");
  const [rows, setRows] = useState(initialConsultations);
  const [counts, setCounts] = useState(initialCountLabels);
  const [status, setStatus] = useState("전체");
  const [searchField, setSearchField] = useState("customer");
  const [input, setInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [checked, setChecked] = useState(() => new Set());
  const [selected, setSelected] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const filtered = useMemo(() => rows.filter((row) => (status === "전체" || row.status === status) && (!keyword || String(row[searchField]).toLowerCase().includes(keyword.toLowerCase()))), [rows, status, keyword, searchField]);
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const allChecked = pageRows.length > 0 && pageRows.every((row) => checked.has(row.id));

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "F8" && !modalOpen) {
        event.preventDefault();
        setKeyword(input.trim());
        setPage(1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [input, modalOpen]);

  const toast = (message) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2500);
  };
  const doSearch = (event) => { event.preventDefault(); setKeyword(input.trim()); setPage(1); };
  const resetSearch = () => { setInput(""); setKeyword(""); setPage(1); };
  const toggleAll = () => setChecked((current) => { const next = new Set(current); pageRows.forEach((row) => allChecked ? next.delete(row.id) : next.add(row.id)); return next; });
  const toggleOne = (id) => setChecked((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; });

  function createConsultation(form) {
    const newRow = {
      id: `TEMP-${Date.now()}`, no: rows.length + 1,
      date: new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short", hour12: false }).format(new Date()),
      status: form.status, manager: "현재사용자", brand: form.brand || "-", interest: form.interest || "-",
      customer: form.customer, contact: form.mobile, region: form.address || "-", detail: form.detail,
    };
    setRows((current) => [newRow, ...current]);
    setCounts((current) => ({ ...current, 전체: current.전체 + 1, [form.status]: current[form.status] + 1 }));
    setStatus("전체"); setKeyword(""); setInput(""); setPage(1); setModalOpen(false);
    toast("신규 상담이 프론트 임시 데이터로 등록되었습니다.");
  }

  const columns = [
    ["no", "No.", "col-no"], ["date", "접수일시", "col-date"], ["status", "상태", "col-status"], ["manager", "담당자", "col-manager"],
    ["brand", "브랜드", "col-brand"], ["interest", "관심제품", "col-product"], ["customer", "고객명", "col-customer"],
    ["contact", "연락처", "col-contact"], ["region", "주소(지역)", "col-region"], ["detail", "상담내역(최근 1건)", "col-detail"],
  ];

  return (
    <section className="consult-list-page">
      <header><h2>상담목록</h2><span>프론트엔드 mock 데이터</span></header>
      <div className="consult-list-toolbar">
        <div>{canCreate && <button type="button" className="primary" onClick={() => setModalOpen(true)}>상담등록</button>}<button type="button" onClick={() => toast("프론트 개발 모드에서는 다운로드하지 않습니다.")}>엑셀다운로드</button></div>
        <form onSubmit={doSearch}><select value={searchField} onChange={(event) => setSearchField(event.target.value)}>{Object.entries(searchFields).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={input} placeholder="검색어를 입력하세요" onChange={(event) => setInput(event.target.value)} /><button type="submit" className="primary">검색(F8)</button><button type="button" onClick={resetSearch}>초기화</button></form>
        <strong>{checked.size}건 선택</strong>
      </div>
      <div className="consult-list-tabs">{statuses.map((item) => <button type="button" key={item} className={status === item ? "active" : ""} onClick={() => { setStatus(item); setPage(1); }}>{item}<span>{counts[item].toLocaleString("ko-KR")}건</span></button>)}</div>
      <div className="consult-list-table-wrap">
        <table className="consult-list-table">
          <colgroup><col className="col-check" />{columns.map(([key, , className]) => <col key={key} className={className} />)}</colgroup>
          <thead><tr><th><input type="checkbox" aria-label="현재 페이지 전체 선택" checked={allChecked} onChange={toggleAll} /></th>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead>
          <tbody>{pageRows.length ? pageRows.map((row) => <tr key={row.id} className={selected === row.id ? "selected" : ""} onClick={() => setSelected(row.id)}><td><input type="checkbox" aria-label={`${row.no}번 선택`} checked={checked.has(row.id)} onClick={(event) => event.stopPropagation()} onChange={() => toggleOne(row.id)} /></td>{columns.map(([key]) => <td key={key} title={String(row[key])}>{key === "status" ? <StatusBadge status={row.status} /> : key === "customer" ? <MaskedText value={row[key]} type="name" /> : key === "contact" ? <MaskedText value={row[key]} type="phone" /> : key === "region" ? <MaskedText value={row[key]} type="address" /> : row[key]}</td>)}</tr>) : <tr><td className="consult-list-empty" colSpan={11}>검색 결과가 없습니다.</td></tr>}</tbody>
        </table>
      </div>
      <Pagination page={page} onChange={setPage} />
      {modalOpen && <ConsultationCreateModal onClose={() => setModalOpen(false)} onCreate={createConsultation} />}
      {notice && <div className="product-toast" role="status">{notice}</div>}
    </section>
  );
}
