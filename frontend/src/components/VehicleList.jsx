import React from "react";

function VehicleList({
  items,
  isLoading,
  error,
  activeTab,
  editingItemId,
  onDelete,
  onEdit,
  onTabChange,
  tabs,
}) {
  const safeItems = Array.isArray(items) ? items : [];
  const safeTabs = Array.isArray(tabs) ? tabs : [];

  const renderContent = () => {
    if (isLoading) {
      return <div className="state-panel">차량 목록을 불러오는 중입니다.</div>;
    }
    if (error) {
      return (
        <div className="state-panel state-error">
          <strong>차량 목록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      );
    }
    if (safeItems.length === 0) {
      return (
        <div className="state-panel">
          <strong>{activeTab ? "현재 조건에 맞는 차량이 없습니다." : "등록된 차량이 없습니다."}</strong>
          <span>빠른 등록 폼으로 차량을 추가해주세요.</span>
        </div>
      );
    }

    return (
      <div className="asset-table-wrap">
        <table className="asset-table vehicle-table">
          <thead>
            <tr>
              <th>사업자</th>
              <th>차량번호</th>
              <th>차명</th>
              <th>사용자</th>
              <th>소유권</th>
              <th>보험사</th>
              <th>보험 종료일</th>
              <th>보험 D-Day</th>
              <th>리스사</th>
              <th>리스 종료일</th>
              <th>리스 D-Day</th>
              <th>월 리스금액</th>
              <th>리스 납부일</th>
              <th>자동차세 및 기타</th>
              <th className="vehicle-actions-cell">관리</th>
            </tr>
          </thead>
          <tbody>
            {safeItems.map((item) => (
              <tr
                key={item.id}
                className={editingItemId === item.id ? "vehicle-row editing" : "vehicle-row"}
              >
                <td>{formatText(item.company_name)}</td>
                <td><strong>{item.vehicle_number}</strong></td>
                <td>{item.vehicle_name}</td>
                <td>{formatText(item.driver_name)}</td>
                <td><span className="software-type-badge">{item.ownership_type}</span></td>
                <td>{formatText(item.insurance_company)}</td>
                <td>{formatText(item.insurance_end_date)}</td>
                <td><DDayBadge dateValue={item.insurance_end_date} soonDays={30} /></td>
                <td>{formatText(item.lease_company)}</td>
                <td>{formatText(item.lease_end_date)}</td>
                <td><DDayBadge dateValue={item.lease_end_date} soonDays={60} /></td>
                <td>{formatCurrency(item.monthly_lease_amount)}</td>
                <td>{formatText(item.lease_payment_day)}</td>
                <td className="vehicle-note-cell">{formatText(item.tax_note)}</td>
                <td className="vehicle-actions-cell">
                  <div className="software-row-actions">
                    <button
                      type="button"
                      className="secondary-button software-action-button"
                      onClick={() => onEdit(item)}
                    >
                      수정
                    </button>
                    <button
                      type="button"
                      className="danger-button software-action-button"
                      onClick={() => onDelete(item)}
                    >
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <section className="content-panel vehicle-list-panel">
      <div className="section-heading">
        <div>
          <h2>차량 목록</h2>
          <p>소유권과 만기 임박 기준으로 최신 등록순으로 표시됩니다.</p>
        </div>
      </div>

      <div className="software-list-controls vehicle-list-controls">
        <div className="software-tabs" aria-label="법인차량 탭">
          {safeTabs.map((tab) => (
            <button
              type="button"
              key={tab.label}
              className={activeTab === tab.value ? "software-tab active" : "software-tab"}
              onClick={() => onTabChange(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {renderContent()}
    </section>
  );
}

function DDayBadge({ dateValue, soonDays }) {
  const daysLeft = getDaysUntilDate(dateValue);
  const status = getDDayStatus(daysLeft, soonDays);
  return (
    <span className={`software-expiration-badge software-expiration-${status.tone}`}>
      {status.label}
    </span>
  );
}

function getDDayStatus(daysLeft, soonDays) {
  if (daysLeft === null) {
    return { label: "날짜 없음", tone: "muted" };
  }
  if (daysLeft < 0) {
    return { label: "만료됨", tone: "expired" };
  }
  return {
    label: `D-${daysLeft}`,
    tone: daysLeft <= soonDays ? "danger" : "normal",
  };
}

export function getDaysUntilDate(dateValue) {
  if (!dateValue) {
    return null;
  }

  const [year, month, day] = String(dateValue).split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const targetStart = new Date(year, month - 1, day);
  return Math.ceil((targetStart.getTime() - todayStart.getTime()) / 86400000);
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return Number(value || 0).toLocaleString("ko-KR");
}

export default VehicleList;
