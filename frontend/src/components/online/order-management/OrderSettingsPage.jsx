import React, { useEffect, useState } from "react";
import { createOrderChannel, getOrderChannels, updateOrderChannel } from "../../../api/client.js";

const EMPTY_CHANNEL = { name: "", code: "", description: "", is_active: true, is_default: false };

function OrderSettingsPage({ currentUser }) {
  const isAdmin = currentUser?.role === "admin";
  const [channels, setChannels] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getOrderChannels()
      .then((items) => { if (alive) setChannels(items); })
      .catch((failure) => { if (alive) setError(failure.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  function openForm(channel = null) {
    setEditingId(channel?.id ?? null);
    setForm(channel ? {
      name: channel.name, code: channel.code, description: channel.description,
      is_active: channel.is_active, is_default: channel.is_default,
    } : { ...EMPTY_CHANNEL });
    setError("");
  }

  async function saveChannel(event) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const payload = { ...form, name: form.name.trim(), description: form.description.trim() };
      if (editingId === null) {
        await createOrderChannel(payload);
      } else {
        await updateOrderChannel(editingId, {
          name: payload.name, description: payload.description,
          is_active: payload.is_active, is_default: payload.is_default,
        });
      }
      setChannels(await getOrderChannels());
      setForm(null);
      setEditingId(null);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className="online-order-panel online-order-channel-settings">
        <div className="online-order-panel-heading online-order-channel-heading">
          <h3>채널 설정</h3>
          {isAdmin && <button type="button" className="secondary-button" onClick={() => openForm()}>+ 채널 추가</button>}
        </div>
        {error && <p className="online-order-channel-error" role="alert">{error}</p>}
        {loading ? <p className="online-order-empty">채널 목록을 불러오는 중입니다.</p> : (
          <div className="online-order-table-scroll">
            <table className="online-order-skeleton-table online-order-channel-table">
              <thead><tr><th>채널명</th><th>채널 코드</th><th>설명</th><th>사용 여부</th><th>가공 지원 여부</th><th>기본 채널</th><th>관리</th></tr></thead>
              <tbody>
                {channels.map((channel) => <tr key={channel.id}>
                  <td>{channel.name}</td><td>{channel.code}</td><td>{channel.description || "-"}</td>
                  <td>{channel.is_active ? "사용" : "미사용"}</td>
                  <td>{channel.processing_supported ? "지원" : "준비중"}</td>
                  <td>{channel.is_default ? "기본" : "-"}</td>
                  <td>{isAdmin ? <button type="button" className="secondary-button" onClick={() => openForm(channel)}>수정</button> : "-"}</td>
                </tr>)}
                {channels.length === 0 && <tr><td colSpan="7" className="online-order-empty-cell">등록된 채널이 없습니다.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
        {isAdmin && form && <form className="online-order-channel-form" onSubmit={saveChannel}>
          <h4>{editingId === null ? "채널 추가" : "채널 수정"}</h4>
          <div className="online-order-form-grid">
            <label>채널명<input required maxLength="100" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
            <label>채널 코드<input required maxLength="50" pattern="[a-z0-9_]+" value={form.code} readOnly={editingId !== null} onChange={(event) => setForm({ ...form, code: event.target.value })} /></label>
            <label>설명<input maxLength="1000" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          </div>
          {editingId !== null && <p>채널 코드는 생성 후 변경할 수 없습니다.</p>}
          <div className="online-order-channel-checks">
            <label><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked, is_default: event.target.checked ? form.is_default : false })} /> 사용</label>
            <label><input type="checkbox" checked={form.is_default} disabled={!form.is_active || (editingId !== null && channels.some((channel) => channel.id === editingId && channel.is_default))} onChange={(event) => setForm({ ...form, is_default: event.target.checked })} /> 기본 채널</label>
          </div>
          <div className="online-order-channel-actions">
            <button type="submit" className="primary-action" disabled={saving}>{saving ? "저장 중" : "저장"}</button>
            <button type="button" className="secondary-button" onClick={() => setForm(null)} disabled={saving}>취소</button>
          </div>
        </form>}
      </section>
      <section className="online-order-panel"><h3>파일 설정</h3><div className="online-order-setting-row"><span>허용 파일 형식</span><strong>.xlsx / .xls</strong></div><div className="online-order-setting-row"><span>최대 파일 크기</span><strong>추후 확정</strong></div></section>
      <section className="online-order-panel"><h3>가공 설정</h3><p className="online-order-empty">자동 가공 기능 준비 중</p></section>
    </>
  );
}

export default OrderSettingsPage;
