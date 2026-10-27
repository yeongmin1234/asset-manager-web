import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "./contexts/AuthContext";
import {
  activateMarketplace,
  createMarketplace,
  deactivateMarketplace,
  getMarketplaces,
  getMarketplaceSalesUsage,
  marketplaceApiConfigured,
} from "./services/marketplaceService";

const empty = { code: "", name: "", marketplace_type: "online_market", description: "", sort_order: "0" };
const typeLabels = {
  online_market: "온라인 마켓",
  department_store: "백화점",
  own_mall: "자사몰",
  offline: "오프라인",
  other: "기타",
};

export default function MarketplaceSelector({ value, onChange, onNotice, children }) {
  const { currentUser } = useAuth();
  const isAdmin = currentUser.accountType === "admin";
  const [tab, setTab] = useState("select");
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const load = async () => {
    if (!marketplaceApiConfigured) return;
    try {
      const result = await getMarketplaces();
      const loaded = await Promise.all((result.items || []).map(async (item) => ({
        ...item,
        is_deleted: false,
        used_for_sales: Boolean(item.used_for_sales || item.sale_count) || await getMarketplaceSalesUsage(item.id),
      })));
      setItems(loaded);
      setError("");
    } catch (reason) {
      setError(reason.message);
    }
  };
  useEffect(() => { load(); }, []);

  const activeItems = useMemo(
    () => items.filter((item) => item.status === "active" && !item.is_deleted).sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)),
    [items],
  );
  const visibleItems = useMemo(() => items.filter((item) => {
    const keywordMatch = `${item.code} ${item.name}`.toLowerCase().includes(query.trim().toLowerCase());
    const statusMatch = statusFilter === "all"
      || (statusFilter === "deleted" ? item.is_deleted : !item.is_deleted && item.status === statusFilter);
    return keywordMatch && statusMatch && (typeFilter === "all" || item.marketplace_type === typeFilter);
  }), [items, query, statusFilter, typeFilter]);

  const submit = async (event) => {
    event.preventDefault();
    if (event.nativeEvent?.isComposing || submitting) return;
    if (!form.code.trim() || !form.name.trim()) {
      setError("마켓 코드와 마켓명을 입력하십시오.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      let created;
      if (marketplaceApiConfigured) {
        created = await createMarketplace({ ...form, sort_order: Number(form.sort_order), description: form.description || null });
        await load();
      } else {
        const code = form.code.trim().toUpperCase();
        if (items.some((item) => item.code === code || item.name === form.name.trim())) {
          throw new Error("이미 등록된 마켓 코드 또는 이름입니다.");
        }
        created = {
          id: `local-${Date.now()}`,
          ...form,
          code,
          name: form.name.trim(),
          sort_order: Number(form.sort_order),
          status: "active",
          is_deleted: false,
          used_for_sales: false,
        };
        setItems((current) => [...current, created]);
      }
      onChange(created.id);
      setForm(empty);
      setTab("select");
      onNotice(marketplaceApiConfigured ? "마켓을 등록했습니다." : "마켓을 현재 화면에 임시 등록했습니다.");
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSubmitting(false);
    }
  };

  const submitOnEnter = (event) => {
    if (event.key !== "Enter" || event.target.tagName === "TEXTAREA") return;
    if (event.isComposing || event.nativeEvent?.isComposing || submitting) return;
    event.preventDefault();
    event.currentTarget.requestSubmit();
  };

  const changeStatus = async (item) => {
    const next = item.status === "active" ? "inactive" : "active";
    try {
      if (marketplaceApiConfigured) {
        if (next === "active") await activateMarketplace(item.id);
        else await deactivateMarketplace(item.id);
        await load();
      } else {
        setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, status: next } : entry));
      }
      if (next === "inactive" && String(value) === String(item.id)) onChange("");
      onNotice(next === "active" ? "마켓을 사용재개했습니다." : "마켓을 사용중지했습니다.");
    } catch (reason) {
      setError(reason.message);
    }
  };

  const toggleDeleted = (item) => {
    if (!item.is_deleted && item.used_for_sales) {
      setError("판매에 사용된 마켓은 삭제할 수 없습니다.");
      return;
    }
    setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_deleted: !entry.is_deleted } : entry));
    if (!item.is_deleted && String(value) === String(item.id)) onChange("");
    onNotice(item.is_deleted ? "마켓을 복구했습니다." : "마켓을 현재 화면에서 삭제 처리했습니다.");
  };

  return (
    <div className="marketplace-selector">
      <div className="marketplace-tabs" role="tablist">
        <button type="button" className={tab === "select" ? "active" : ""} onClick={() => setTab("select")}>마켓 선택</button>
        <button type="button" className={tab === "list" ? "active" : ""} onClick={() => setTab("list")}>마켓 목록</button>
      </div>
      {tab === "select" ? (
        <div className="marketplace-select-tab">
          <label>마켓선택
            <select value={value} onChange={(event) => onChange(event.target.value)}>
              <option value="">선택</option>
              {activeItems.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          {children}
          <section className="marketplace-add-section">
            <h3>새 마켓 추가</h3>
            <form className="marketplace-add-form" onSubmit={submit} onKeyDown={submitOnEnter}>
              <label>마켓 코드<input value={form.code} maxLength={50} onChange={(e) => setForm((current) => ({ ...current, code: e.target.value }))} /></label>
              <label>마켓명<input value={form.name} maxLength={100} onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))} /></label>
              <label>마켓 유형<select value={form.marketplace_type} onChange={(e) => setForm((current) => ({ ...current, marketplace_type: e.target.value }))}>{Object.entries(typeLabels).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label>
              <label className="description">설명<textarea value={form.description} maxLength={500} onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))} /></label>
              <label>정렬 순서<input type="number" min="0" value={form.sort_order} onChange={(e) => setForm((current) => ({ ...current, sort_order: e.target.value }))} /></label>
              {error && <small>{error}</small>}
              <footer><button type="button" onClick={() => { setForm(empty); setError(""); }}>초기화</button><button type="submit" className="primary" disabled={submitting}>{submitting ? "등록 중" : "추가"}</button></footer>
            </form>
          </section>
        </div>
      ) : (
        <div className="marketplace-list-tab">
          <div className="marketplace-list-filters">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="마켓 코드 또는 마켓명" />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">상태 전체</option><option value="active">사용 중</option><option value="inactive">사용중지</option><option value="deleted">삭제됨</option></select>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="all">유형 전체</option>{Object.entries(typeLabels).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select>
            <button type="button" onClick={load}>새로고침</button>
          </div>
          <div className="marketplace-list-table-wrap">
            <table>
              <thead><tr><th>마켓 코드</th><th>마켓명</th><th>마켓 유형</th><th>상태</th><th>판매 사용</th><th>정렬 순서</th><th>관리</th></tr></thead>
              <tbody>
                {visibleItems.map((item) => (
                  <tr key={item.id}>
                    <td title={item.code}>{item.code}</td><td title={item.name}>{item.name}</td><td>{typeLabels[item.marketplace_type] || "-"}</td>
                    <td><span className={`marketplace-status marketplace-status--${item.is_deleted ? "deleted" : item.status}`}>{item.is_deleted ? "삭제됨" : item.status === "active" ? "사용 중" : "사용중지"}</span></td>
                    <td>{item.used_for_sales ? "사용" : "미사용"}</td><td>{item.sort_order}</td>
                    <td>{isAdmin && <div className="marketplace-actions">{!item.is_deleted && <button type="button" onClick={() => changeStatus(item)}>{item.status === "active" ? "사용중지" : "사용재개"}</button>}<button type="button" onClick={() => toggleDeleted(item)}>{item.is_deleted ? "복구" : "삭제"}</button></div>}</td>
                  </tr>
                ))}
                {!visibleItems.length && <tr><td className="marketplace-list-empty" colSpan={7}>등록된 마켓이 없습니다.</td></tr>}
              </tbody>
            </table>
          </div>
          {error && <small>{error}</small>}
        </div>
      )}
    </div>
  );
}
