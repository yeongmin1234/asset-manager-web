import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  confirmRecallOrder, downloadRecallOrderBatch, exportRecallOrders,
  getRecallOrders, getRecallOrderSummary, previewRecallOrders,
} from "../../api/client.js";
import { displayRecallStatus, formatPhoneForDisplay, formatRecallDate, recallStatusClass } from "./onlineDisplayUtils.js";
import RecallPageSizeSelect from "./RecallPageSizeSelect.jsx";

const ORDER_LABELS = {
  ORDER_PENDING: "발주 대기",
  ORDER_EXPORTED: "Excel 생성 완료",
  ORDER_CONFIRMED: "발주 완료",
};
const show = (value) => value === null || value === undefined || value === "" ? "" : String(value);

function saveWorkbook({ blob, filename }) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function RecallOrderPreview({ preview, busy, error, onClose, onExport }) {
  return createPortal(
    <div className="online-upload-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section className="online-upload-modal online-order-preview-modal" role="dialog" aria-modal="true" aria-labelledby="online-order-preview-title">
        <header className="online-upload-header">
          <div><h2 id="online-order-preview-title">SCM 발주 Excel 미리보기</h2><p>현재 선택 건을 다시 검증한 후 Excel을 생성합니다.</p></div>
          <button type="button" className="secondary-button" onClick={onClose} disabled={busy}>닫기</button>
        </header>
        <div className="online-order-preview-summary"><span>선택 {preview.item_count}건</span><span>총 주문수량 {preview.total_quantity}</span></div>
        <div className="online-order-preview-scroll">
          <table className="online-order-preview-table">
            <thead><tr>{preview.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>{preview.rows.map((row, index) => <tr key={preview.ids[index]}>{preview.columns.map((column) => <td key={column} title={show(row[column])}>{show(row[column])}</td>)}</tr>)}</tbody>
          </table>
        </div>
        {error && <p className="online-recall-bulk-error" role="alert">{error}</p>}
        <footer className="online-upload-footer">
          <button type="button" className="secondary-button" onClick={onClose} disabled={busy}>취소</button>
          <button type="button" className="primary-action" onClick={onExport} disabled={busy}>{busy ? "생성 중..." : "Excel 생성"}</button>
        </footer>
      </section>
    </div>, document.body,
  );
}

function RecallOrderTab({ isAdmin = false, pageSize = 20, onPageSizeChange = () => {} }) {
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({ pending_count: 0, exported_count: 0, confirmed_count: 0 });
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [status, setStatus] = useState("ORDER_PENDING");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const selectAllRef = useRef(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([getRecallOrders({ status, page, page_size: pageSize }), getRecallOrderSummary()])
      .then(([list, counts]) => {
        if (!active) return;
        setItems(list.items || []);
        setTotal(list.total || 0);
        setTotalPages(list.total_pages || 1);
        setSummary(counts);
        setSelectedIds(new Set());
      })
      .catch((caught) => { if (active) setError(caught?.message || "SCM 발주 대상을 불러오지 못했습니다."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [status, page, pageSize, refreshKey]);

  const pendingItems = items.filter((item) => item.order_status === "ORDER_PENDING");
  const selectedOnPage = pendingItems.filter((item) => selectedIds.has(item.id)).length;
  const allSelected = pendingItems.length > 0 && selectedOnPage === pendingItems.length;
  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = selectedOnPage > 0 && !allSelected;
  }, [selectedOnPage, allSelected]);

  const toggle = (id) => setSelectedIds((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });

  const openPreview = async () => {
    if (!selectedIds.size || busy) return;
    setBusy(true);
    setError("");
    try {
      setPreview(await previewRecallOrders([...selectedIds]));
      setPreviewError("");
    } catch (caught) {
      setError(caught?.message || "SCM Excel 미리보기에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const exportSelected = async () => {
    if (!preview || busy) return;
    setBusy(true);
    setPreviewError("");
    try {
      const workbook = await exportRecallOrders(preview.ids);
      setPreview(null);
      setSelectedIds(new Set());
      setRefreshKey((value) => value + 1);
      setMessage(`${preview.item_count}건의 SCM Excel을 생성했습니다. 다운로드가 시작되지 않았다면 목록에서 다시 받기를 이용하세요.`);
      try { saveWorkbook(workbook); }
      catch { setError("Excel 생성은 완료됐지만 다운로드가 시작되지 않았습니다. 목록에서 다시 받기를 이용하세요."); }
    } catch (caught) {
      setPreviewError(caught?.message || "SCM Excel 생성에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const downloadBatch = async (batchId) => {
    setBusy(true);
    setError("");
    try { saveWorkbook(await downloadRecallOrderBatch(batchId)); }
    catch (caught) { setError(caught?.message || "SCM Excel을 다시 받지 못했습니다."); }
    finally { setBusy(false); }
  };

  const confirm = async (id) => {
    if (!window.confirm("이 건의 SCM 발주가 완료되었습니까?")) return;
    setBusy(true);
    setError("");
    try {
      await confirmRecallOrder(id);
      setMessage("발주 완료 상태로 변경했습니다.");
      setRefreshKey((value) => value + 1);
    } catch (caught) { setError(caught?.message || "발주 완료 처리에 실패했습니다."); }
    finally { setBusy(false); }
  };

  return (
    <section className="online-recall-list online-order-panel" aria-label="SCM 발주 대상">
      <div className="online-order-summary">
        {[["pending_count", "발주 대기"], ["exported_count", "Excel 생성 완료"], ["confirmed_count", "발주 완료"]].map(([key, label]) =>
          <div key={key}><span>{label}</span><strong>{summary[key] ?? 0}</strong></div>)}
      </div>
      <div className="online-order-toolbar">
        <label>주문 상태 <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} disabled={busy}>
          <option value="ORDER_PENDING">발주 대기</option><option value="ORDER_EXPORTED">Excel 생성 완료</option><option value="ORDER_CONFIRMED">발주 완료</option><option value="">전체</option>
        </select></label>
        <span>선택 {selectedIds.size}건</span>
        <RecallPageSizeSelect value={pageSize} onChange={(value) => { setPage(1); setSelectedIds(new Set()); onPageSizeChange(value); }} disabled={busy} />
        <button type="button" className="primary-action" onClick={openPreview} disabled={!selectedIds.size || busy || loading}>SCM 발주 Excel 생성</button>
      </div>
      {message && <p className="online-recall-bulk-message" role="status">{message}</p>}
      {error && <p className="online-recall-bulk-error" role="alert">{error}</p>}
      <div className="online-recall-table-wrap">
        <table className="online-recall-table online-order-table">
          <thead><tr>
            <th><input ref={selectAllRef} type="checkbox" aria-label="현재 페이지 발주 대기 전체 선택" checked={allSelected} disabled={!pendingItems.length || loading || busy} onChange={(event) => setSelectedIds(new Set(event.target.checked ? pendingItems.map((item) => item.id) : []))} /></th>
            {"신청일자,성함,연락처,주소지,수량,메모,현재 리콜 상태,주문 상태,작업".split(",").map((label) => <th key={label}>{label}</th>)}
          </tr></thead>
          <tbody>{loading ? <tr><td colSpan={10} className="online-recall-empty">SCM 발주 대상을 불러오는 중입니다.</td></tr> : items.length ? items.map((item) => <tr key={item.id}>
            <td><input type="checkbox" aria-label={`${item.customer_name} 발주 선택`} checked={selectedIds.has(item.id)} disabled={item.order_status !== "ORDER_PENDING" || busy} onChange={() => toggle(item.id)} /></td>
            <td>{formatRecallDate(item.application_date)}</td><td>{item.customer_name}</td>
            <td>{formatPhoneForDisplay(item.phone_original)}</td>
            <td className="online-recall-long-cell" title={item.address}><span>{item.address}</span></td>
            <td>{item.quantity ?? "-"}</td>
            <td className="online-recall-long-cell" title={item.memo || ""}><span>{item.memo || "-"}</span></td>
            <td><span className={`online-recall-status ${recallStatusClass(item.current_status)}`}>{displayRecallStatus(item.current_status)}</span></td>
            <td><span className={`online-order-status online-order-status-${item.order_status}`}>{ORDER_LABELS[item.order_status] || item.order_status}</span></td>
            <td className="online-order-row-actions">
              {item.order_batch_id && <button type="button" className="secondary-button" disabled={busy} onClick={() => downloadBatch(item.order_batch_id)}>다시 받기</button>}
              {isAdmin && item.order_status === "ORDER_EXPORTED" && <button type="button" className="secondary-button" disabled={busy} onClick={() => confirm(item.id)}>발주 완료</button>}
            </td>
          </tr>) : <tr><td colSpan={10} className="online-recall-empty">해당 SCM 발주 대상이 없습니다.</td></tr>}</tbody>
        </table>
      </div>
      <div className="online-recall-pagination"><span>총 {total}건 · {page}/{totalPages} 페이지</span><div>
        <button type="button" className="secondary-button" disabled={page <= 1 || loading || busy} onClick={() => setPage(page - 1)}>이전</button>
        <button type="button" className="secondary-button" disabled={page >= totalPages || loading || busy} onClick={() => setPage(page + 1)}>다음</button>
      </div></div>
      {preview && <RecallOrderPreview preview={preview} busy={busy} error={previewError} onClose={() => setPreview(null)} onExport={exportSelected} />}
    </section>
  );
}

export default RecallOrderTab;
