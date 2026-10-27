import React, { useState } from "react";
import { Modal } from "./components/common/CommonUI";

const today = () => new Date().toISOString().slice(0, 10);

export default function EmployeeLifecycleModal({ type, count, employee, onClose, onConfirm }) {
  const [form, setForm] = useState(type === "resign"
    ? { date: today(), reason: "" }
    : { date: today(), store: employee?.store || "", role: employee?.role || "직원", note: "" });
  const [error, setError] = useState("");
  const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  function submit(event) {
    event.preventDefault();
    if (!form.date) {
      setError(type === "resign" ? "퇴사일을 입력하십시오." : "재입사일을 입력하십시오.");
      return;
    }
    if (type === "rehire" && (!form.store.trim() || !form.role)) {
      setError("매장과 직책을 입력하십시오.");
      return;
    }
    onConfirm(form);
  }

  return (
    <Modal title={type === "resign" ? "직원 퇴사 처리" : "직원 재입사"} onClose={onClose}>
      <form className="employee-lifecycle-modal" onSubmit={submit}>
        <p>{type === "resign" ? `선택한 ${count}명의 직원을 퇴사 처리합니다.` : "퇴사 이력은 유지하고 재직 상태로 변경합니다."}</p>
        <label><span>{type === "resign" ? "퇴사일" : "재입사일"}</span><input type="date" value={form.date} onChange={(event) => set("date", event.target.value)} /></label>
        {type === "resign" ? (
          <label><span>퇴사 사유</span><textarea value={form.reason} onChange={(event) => set("reason", event.target.value)} placeholder="선택 입력" /></label>
        ) : (
          <>
            <label><span>매장</span><input value={form.store} onChange={(event) => set("store", event.target.value)} /></label>
            <label><span>직책</span><select value={form.role} onChange={(event) => set("role", event.target.value)}>{["직원", "부매니저", "매니저"].map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>비고</span><textarea value={form.note} onChange={(event) => set("note", event.target.value)} /></label>
          </>
        )}
        {error && <p className="employee-lifecycle-error">{error}</p>}
        <footer><button type="button" onClick={onClose}>취소</button><button className="primary">{type === "resign" ? "퇴사 처리" : "재입사"}</button></footer>
      </form>
    </Modal>
  );
}
