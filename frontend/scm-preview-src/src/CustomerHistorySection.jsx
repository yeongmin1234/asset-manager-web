import React from "react";

export default function CustomerHistorySection({ title, kind, rows, searched, selectedId, onSelect }) {
  const columns = kind === "sales"
    ? [["date", "일시"], ["person", "고객명 / 수취인"], ["phones", "전화 / 핸드폰"], ["type", "구분"], ["status", "상태"], ["product", "제품명"]]
    : [["date", "일시"], ["name", "고객명"], ["contact", "연락처"], ["type", "구분"], ["status", "상태"], ["product", kind === "consultations" ? "관심제품" : "제품명"]];

  const display = (row, key) => {
    if (key === "person") return `${row.name} / ${row.recipient}`;
    if (key === "phones") return `${row.phone} / ${row.mobile}`;
    return row[key];
  };

  return (
    <section className="consult-create-history">
      <h3>{title}</h3>
      <table>
        <thead><tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>
          {!searched || !rows.length ? (
            <tr><td className="consult-create-history__empty" colSpan={6}>{searched ? "검색 결과가 없습니다" : "고객명/연락처 검색어를 입력하십시오"}</td></tr>
          ) : rows.map((row) => (
            <tr key={row.id} className={selectedId === row.id ? "selected" : ""} onClick={() => onSelect(row)}>
              {columns.map(([key]) => <td key={key} title={display(row, key)}>{display(row, key)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
