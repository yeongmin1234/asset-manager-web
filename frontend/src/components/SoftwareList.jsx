import React, { useState } from "react";

function SoftwareList({
  items,
  isLoading,
  error,
  filters,
  activeTab,
  editingItemId,
  onDelete,
  onEdit,
  onFilterChange,
  onTabChange,
  tabs,
}) {
  const [licenseModalItem, setLicenseModalItem] = useState(null);
  const [copyMessage, setCopyMessage] = useState("");
  const safeItems = Array.isArray(items) ? items : [];
  const safeTabs = Array.isArray(tabs) ? tabs : [];
  const hasActiveFilters = Boolean(activeTab || filters.expiration_status);

  const openLicenseModal = (item) => {
    setLicenseModalItem(item);
    setCopyMessage("");
  };

  const closeLicenseModal = () => {
    setLicenseModalItem(null);
    setCopyMessage("");
  };

  const handleCopyLicense = async () => {
    const licenseKey = licenseModalItem?.license_key || "";
    if (!licenseKey) {
      return;
    }

    try {
      await navigator.clipboard.writeText(licenseKey);
      setCopyMessage("복사되었습니다.");
    } catch {
      setCopyMessage("복사하지 못했습니다.");
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return <div className="state-panel">SW 목록을 불러오는 중입니다.</div>;
    }
    if (error) {
      return (
        <div className="state-panel state-error">
          <strong>SW 목록을 불러오지 못했습니다.</strong>
          <span className="state-detail">{error}</span>
        </div>
      );
    }
    if (safeItems.length === 0) {
      return (
        <div className="state-panel">
          <strong>{hasActiveFilters ? "현재 조건에 맞는 SW가 없습니다." : "등록된 SW가 없습니다."}</strong>
          <span>빠른 등록 폼으로 소프트웨어를 추가해주세요.</span>
        </div>
      );
    }

    return (
      <div className="asset-table-wrap">
        <table className="asset-table software-table">
          <thead>
            <tr>
              <th>소프트웨어명</th>
              <th>소유</th>
              <th>라이선스 구분</th>
              <th>수량</th>
              <th>가격</th>
              <th>만료일</th>
              <th>라이선스키/CDKEY</th>
              <th>관리</th>
            </tr>
          </thead>
          <tbody>
            {safeItems.map((item) => (
              <tr
                key={item.id}
                className={editingItemId === item.id ? "software-row editing" : "software-row"}
              >
                <td>
                  <div className="asset-name">
                    <strong>{item.name}</strong>
                    <span>ID {item.id}</span>
                  </div>
                </td>
                <td>{item.owner_name || "-"}</td>
                <td><span className="software-type-badge">{item.license_type}</span></td>
                <td>{Number(item.quantity || 0).toLocaleString("ko-KR")}</td>
                <td className="software-price-cell">{formatPrice(item.price_amount)}</td>
                <td>
                  <div className="software-expire-cell">
                    <span>{item.expire_date || "-"}</span>
                    <ExpirationBadge expireDate={item.expire_date} />
                  </div>
                </td>
                <td className="software-license-key-cell">
                  {item.license_key ? (
                    <button
                      type="button"
                      className="secondary-button software-license-view-button"
                      onClick={() => openLicenseModal(item)}
                    >
                      라이선스 보기
                    </button>
                  ) : (
                    "-"
                  )}
                </td>
                <td>
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
    <section className="content-panel software-list-panel">
      <div className="section-heading">
        <div>
          <h2>SW 목록</h2>
          <p>탭과 만료 상태를 기준으로 최신 등록순으로 표시됩니다.</p>
        </div>
      </div>

      <div className="software-list-controls">
        <div className="software-tabs" aria-label="SW 구분 탭">
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

        <div className="software-filter-grid">
          <label className="field">
            <span>만료 상태</span>
            <select
              value={filters.expiration_status}
              onChange={(event) =>
                onFilterChange({ ...filters, expiration_status: event.target.value })
              }
            >
              <option value="">전체</option>
              <option value="within_30">만료 예정 30일 이내</option>
              <option value="within_60">만료 예정 60일 이내</option>
              <option value="within_90">만료 예정 90일 이내</option>
              <option value="expired">만료됨</option>
              <option value="no_date">만료일 없음</option>
            </select>
          </label>
        </div>
      </div>

      {renderContent()}

      {licenseModalItem ? (
        <div className="software-license-modal-backdrop" role="presentation">
          <section
            className="software-license-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="software-license-modal-title"
          >
            <div className="software-license-modal-heading">
              <div>
                <h3 id="software-license-modal-title">라이선스키 / CDKEY</h3>
                <p>{licenseModalItem.name || "-"}</p>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="라이선스 보기 닫기"
                onClick={closeLicenseModal}
              >
                ×
              </button>
            </div>

            <dl className="software-license-info">
              <div>
                <dt>소프트웨어명</dt>
                <dd>{licenseModalItem.name || "-"}</dd>
              </div>
              <div>
                <dt>소유</dt>
                <dd>{licenseModalItem.owner_name || "-"}</dd>
              </div>
              <div className="software-license-key-detail">
                <dt>라이선스키/CDKEY</dt>
                <dd>{licenseModalItem.license_key || "-"}</dd>
              </div>
            </dl>

            <div className="software-license-modal-actions">
              {copyMessage ? <span className="inline-success">{copyMessage}</span> : null}
              <button type="button" className="secondary-button" onClick={handleCopyLicense}>
                복사
              </button>
              <button type="button" className="primary-action" onClick={closeLicenseModal}>
                닫기
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function ExpirationBadge({ expireDate }) {
  const status = getExpirationStatus(expireDate);
  return (
    <span className={`software-expiration-badge software-expiration-${status.tone}`}>
      {status.label}
    </span>
  );
}

function getExpirationStatus(expireDate) {
  const daysLeft = getDaysUntilExpire(expireDate);
  if (daysLeft === null) {
    return { label: "만료일 없음", tone: "muted" };
  }
  if (daysLeft < 0) {
    return { label: "만료됨", tone: "expired" };
  }
  if (daysLeft <= 30) {
    return { label: "30일 이내", tone: "danger" };
  }
  if (daysLeft <= 60) {
    return { label: "60일 이내", tone: "warning" };
  }
  if (daysLeft <= 90) {
    return { label: "90일 이내", tone: "notice" };
  }
  return { label: "정상", tone: "normal" };
}

function getDaysUntilExpire(expireDate) {
  if (!expireDate) {
    return null;
  }

  const [year, month, day] = String(expireDate).split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const expireStart = new Date(year, month - 1, day);
  return Math.ceil((expireStart.getTime() - todayStart.getTime()) / 86400000);
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "-";
  }
  return `₩${numericValue.toLocaleString("ko-KR")}`;
}

export default SoftwareList;
