import React, { useState } from "react";

const logisticsRows = [];

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function validateExcelFile(file) {
  if (!file) return "엑셀 파일을 선택해 주세요.";
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["xls", "xlsx"].includes(extension)) return "XLS 또는 XLSX 파일만 선택할 수 있습니다.";
  return "";
}

function FileUploadField({ file, error, onChange }) {
  return (
    <div className="io-file-field">
      <span>파일선택</span>
      <input type="file" accept=".xls,.xlsx" onChange={(event) => onChange(event.target.files?.[0] ?? null)} />
      <div>
        {file ? <><strong>{file.name}</strong><small>{formatFileSize(file.size)} · 화면 검증만 수행</small></> : <small>선택된 파일 없음 · 허용 확장자 .xls, .xlsx</small>}
      </div>
      {error && <p>{error}</p>}
    </div>
  );
}

function UploadResultSummary({ items }) {
  return <div className="io-result-summary">{items.map((item) => <article key={item.label}><span>{item.label}</span><strong>{item.value}건</strong></article>)}</div>;
}

function UploadSection({ type, title, description, guides, buttonLabel, resultItems, onToast }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [resultVisible, setResultVisible] = useState(false);
  const [logisticsType, setLogisticsType] = useState("입고");

  function changeFile(nextFile) {
    setFile(nextFile);
    setError(nextFile ? validateExcelFile(nextFile) : "");
    setResultVisible(false);
  }

  function handleUpload() {
    const validationError = validateExcelFile(file);
    setError(validationError);
    if (validationError) return;
    setResultVisible(true);
    onToast(type === "pickup" ? "집하예약 데이터 검증 완료" : `${logisticsType} 데이터 검증 완료`);
  }

  return (
    <section className="io-upload-section">
      <header><h2>{title}</h2></header>
      <div className="io-upload-body">
        <p className="io-upload-description">{description}</p>
        <ul className="io-guide">{guides.map((guide) => <li key={guide}>{guide}</li>)}</ul>
        {type === "invoice" && (
          <fieldset className="io-logistics-type">
            <legend>물류구분</legend>
            {["입고", "출고"].map((option) => <label key={option}><input type="radio" name="logistics-type" checked={logisticsType === option} onChange={() => setLogisticsType(option)} />{option}</label>)}
          </fieldset>
        )}
        <FileUploadField file={file} error={error} onChange={changeFile} />
        <div className="io-upload-actions"><button type="button" onClick={handleUpload}>{buttonLabel}</button></div>
        {resultVisible && <UploadResultSummary items={resultItems} />}
      </div>
    </section>
  );
}

export function InOutManagement({ onClose }) {
  const [toast, setToast] = useState("");
  function showToast(message) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2500);
  }

  return (
    <section className="io-work-page">
      <header className="io-work-header"><h2>C/S 입출고관리</h2><button type="button" onClick={onClose}>닫기</button></header>
      <div className="io-management-scroll">
        <UploadSection
          type="pickup"
          title="한진기업물류 웹사이트에서 다운로드한 “종합 반품/집하 현황 엑셀” 파일 업로드"
          description="집하예약번호가 입력된 AS·반품·교환 건의 집하 송장번호, 집하 예정일, 집하원 정보를 자동으로 반영하는 임시 화면입니다."
          guides={[
            "한진기업물류 웹사이트에서 다운로드한 엑셀 파일은 바로 처리할 수 없습니다.",
            "MS엑셀 프로그램으로 파일을 열고 다른이름으로 저장해야 합니다.",
            "엑셀 열 순서를 유지해야 하며 XLS, XLSX 파일만 처리 가능합니다.",
            "HTML content type 또는 엑셀 기본 binary 타입이 아닌 경우 처리할 수 없습니다.",
            "binary 타입이 아닐 경우 엑셀 기본 형식으로 다시 저장해 주세요.",
          ]}
          buttonLabel="집하예약 데이터 업로드"
          resultItems={[{ label: "처리 대상", value: 18 }, { label: "송장번호 반영", value: 16 }, { label: "미일치", value: 2 }]}
          onToast={showToast}
        />
        <UploadSection
          type="invoice"
          title="입/출고 송장 일괄 처리"
          description="바코드 스캐너로 처리한 송장번호 엑셀을 기준으로 AS·반품·교환 건의 입고일 또는 출고일을 갱신하는 임시 화면입니다."
          guides={[
            "엑셀 A열의 송장번호를 자동 처리하며 1개 이상의 데이터를 처리할 수 있습니다.",
            "XLS, XLSX 파일만 처리할 수 있습니다.",
            "HTML content type 또는 엑셀 기본 binary 타입이 아닌 경우 처리할 수 없습니다.",
            "binary 타입이 아닐 경우 엑셀 기본 형식으로 다시 저장해 주세요.",
          ]}
          buttonLabel="입/출고 데이터 업로드"
          resultItems={[{ label: "전체", value: 25 }, { label: "정상", value: 23 }, { label: "중복", value: 1 }, { label: "미일치", value: 1 }]}
          onToast={showToast}
        />
      </div>
      {toast && <div className="product-toast" role="status">{toast}</div>}
    </section>
  );
}

export function InOutList({ onClose }) {
  const [status, setStatus] = useState("전체");
  const [page, setPage] = useState(1);
  const [checked, setChecked] = useState(() => new Set());
  const [selectedRow, setSelectedRow] = useState(null);
  const filtered = status === "전체" ? logisticsRows : logisticsRows.filter((row) => row.type === status);
  const totalPages = Math.max(1, Math.ceil(filtered.length / 15));
  const pageRows = filtered.slice((page - 1) * 15, page * 15);
  const allChecked = pageRows.length > 0 && pageRows.every((row) => checked.has(row.id));

  function changeStatus(nextStatus) {
    setStatus(nextStatus);
    setPage(1);
  }
  function toggleAll() {
    setChecked((current) => {
      const next = new Set(current);
      pageRows.forEach((row) => allChecked ? next.delete(row.id) : next.add(row.id));
      return next;
    });
  }
  function toggleOne(id) {
    setChecked((current) => {
      const next = new Set(current);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <section className="io-work-page">
      <header className="io-work-header"><div><h2>C/S 입출고목록</h2><span>{checked.size}건 선택</span></div><button type="button" onClick={onClose}>닫기</button></header>
      <div className="io-status-tabs">{["전체", "입고", "출고"].map((item) => <button type="button" key={item} className={status === item ? "active" : ""} onClick={() => changeStatus(item)}>{item}<span>{item === "전체" ? logisticsRows.length : logisticsRows.filter((row) => row.type === item).length}건</span></button>)}</div>
      <div className="io-table-wrap">
        <table className="io-table">
          <colgroup><col className="io-col-check" /><col className="io-col-no" /><col className="io-col-date" /><col className="io-col-type" /><col className="io-col-manager" /><col className="io-col-department" /><col className="io-col-carrier" /><col className="io-col-invoice" /><col className="io-col-customer" /><col className="io-col-address" /><col className="io-col-contact" /></colgroup>
          <thead><tr><th><input type="checkbox" checked={allChecked} onChange={toggleAll} /></th><th>No.</th><th>처리일시</th><th>구분</th><th>입고담당</th><th>인계부서</th><th>택배사</th><th>송장번호</th><th>고객명</th><th>주소</th><th>연락처</th></tr></thead>
          <tbody>{pageRows.map((row) => <tr key={row.id} className={selectedRow === row.id ? "selected" : ""} onClick={() => setSelectedRow(row.id)}>
            <td><input type="checkbox" checked={checked.has(row.id)} onChange={() => toggleOne(row.id)} onClick={(event) => event.stopPropagation()} /></td><td>{row.no}</td><td>{row.processed}</td><td><span className={`io-type-badge io-type-badge--${row.type}`}>{row.type}</span></td><td>{row.manager}</td><td>{row.department}</td><td>{row.carrier}</td><td>{row.invoice}</td><td>{row.customer}</td><td className="io-address" title={row.address}>{row.address}</td><td>{row.contact}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <nav className="io-pagination"><button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>이전</button>{Array.from({ length: totalPages }, (_, index) => index + 1).map((number) => <button type="button" key={number} className={page === number ? "active" : ""} onClick={() => setPage(number)}>{number}</button>)}<button type="button" disabled={page === totalPages} onClick={() => setPage(page + 1)}>다음</button></nav>
    </section>
  );
}
