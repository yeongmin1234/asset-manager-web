import React, { useEffect, useState } from "react";
import { getVipCustomerStatus, homeAssistantApiConfigured } from "./services/homeAssistantService";

const empty = { total_count: 0, pending_count: 0, in_progress_count: 0, completed_count: 0, customers: [] };

export default function VipCustomerPanel() {
  const [data, setData] = useState(empty);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!homeAssistantApiConfigured) return;
    getVipCustomerStatus().then(setData).catch((reason) => setError(reason.message));
  }, []);
  return (
    <section className="home-work-panel home-vip-panel">
      <h2>오늘의 VIP 고객 응대현황</h2>
      <div className="home-vip-summary">
        <span>전체 <b>{data.total_count}</b></span><span>응대 전 <b>{data.pending_count}</b></span>
        <span>진행 중 <b>{data.in_progress_count}</b></span><span>완료 <b>{data.completed_count}</b></span>
      </div>
      <div className="home-table-scroll">
        <table><thead><tr><th>고객명</th><th>등급</th><th>현재 상태</th><th>담당자</th><th>최근 활동</th></tr></thead>
          <tbody>{data.customers.length ? data.customers.map((item) => (
            <tr key={`${item.source_type}-${item.reference_code}`}><td>{item.masked_customer_name}</td><td>{item.vip_level.toUpperCase()}</td>
              <td><span className={`home-work-status home-work-status--${item.status.replaceAll(" ", "")}`}>{item.status}</span></td>
              <td>{item.assigned_employee_name || "-"}</td><td>{new Date(item.last_activity_at).toLocaleString()}</td></tr>
          )) : <tr><td className="home-empty" colSpan={5}>{error || "오늘 예정된 VIP 고객 응대 업무가 없습니다."}</td></tr>}</tbody>
        </table>
      </div>
    </section>
  );
}
