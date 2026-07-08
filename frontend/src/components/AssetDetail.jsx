import React, { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, deleteAsset, disposeAsset, getAsset, updateAsset } from "../api/client.js";
import AssetForm from "./AssetForm.jsx";
import AssetHistory from "./AssetHistory.jsx";
import StatusBadge from "./StatusBadge.jsx";

function AssetDetail({
  assetId,
  categories,
  departments,
  lookupError,
  onClose,
  onAssetUpdated,
  onAssetDeleted,
}) {
  const [asset, setAsset] = useState(null);
  const [detailState, setDetailState] = useState({ isLoading: false, error: "" });
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editError, setEditError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const categoryName = useMemo(
    () => findLookupName(categories, asset?.category_id),
    [asset?.category_id, categories],
  );
  const departmentName = useMemo(
    () => asset?.department_name || findLookupName(departments, asset?.department_id),
    [asset?.department_id, asset?.department_name, departments],
  );

  useEffect(() => {
    if (!assetId) {
      setAsset(null);
      setDetailState({ isLoading: false, error: "" });
      setIsEditOpen(false);
      setEditError("");
      setActionError("");
      setPendingAction("");
      setHistoryRefreshKey(0);
      return;
    }

    let ignore = false;

    async function loadDetail() {
      setDetailState({ isLoading: true, error: "" });
      try {
        const data = await getAsset(assetId);
        if (!ignore) {
          setAsset(data);
          setDetailState({ isLoading: false, error: "" });
          setActionError("");
        }
      } catch (error) {
        if (!ignore) {
          setAsset(null);
          setDetailState({ isLoading: false, error: error.message });
        }
      }
    }

    loadDetail();

    return () => {
      ignore = true;
    };
  }, [assetId]);

  useEffect(() => {
    if (!assetId || isEditOpen) {
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [assetId, isEditOpen, onClose]);

  const handleBackdropMouseDown = (event) => {
    if (event.target === event.currentTarget) {
      onClose?.();
    }
  };

  const handleSubmitEdit = async (payload) => {
    if (!assetId) {
      return false;
    }

    setIsSubmitting(true);
    setEditError("");

    try {
      const updatedAsset = await updateAsset(assetId, payload);
      setAsset(updatedAsset);
      setIsEditOpen(false);
      await onAssetUpdated(assetId);
      setHistoryRefreshKey((current) => current + 1);
      return true;
    } catch (error) {
      setEditError(error.message);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDispose = async () => {
    if (!assetId || asset?.status === "폐기") {
      return;
    }

    const isConfirmed = window.confirm(
      "이 자산을 폐기 처리하시겠습니까? 상태가 폐기로 변경됩니다.",
    );

    if (!isConfirmed) {
      return;
    }

    setActionError("");
    setPendingAction("dispose");

    try {
      const disposedAsset = await disposeAsset(assetId);
      setAsset(disposedAsset);
      await onAssetUpdated(assetId);
      setHistoryRefreshKey((current) => current + 1);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setPendingAction("");
    }
  };

  const handleDelete = async () => {
    if (!assetId) {
      return;
    }

    const isConfirmed = window.confirm(
      "이 자산을 삭제하시겠습니까? 데이터는 목록에서 숨겨집니다.",
    );

    if (!isConfirmed) {
      return;
    }

    setActionError("");
    setPendingAction("delete");

    try {
      await deleteAsset(assetId);
      await onAssetDeleted();
    } catch (error) {
      setActionError(error.message);
    } finally {
      setPendingAction("");
    }
  };

  if (!assetId) {
    return null;
  }

  if (detailState.isLoading) {
    return (
      <DetailModalShell onClose={onClose} onBackdropMouseDown={handleBackdropMouseDown}>
        <div className="state-panel">자산 상세 정보를 불러오는 중입니다.</div>
      </DetailModalShell>
    );
  }

  if (detailState.error) {
    return (
      <DetailModalShell onClose={onClose} onBackdropMouseDown={handleBackdropMouseDown}>
        <div className="state-panel state-error">
          <strong>자산 상세 정보를 불러오지 못했습니다.</strong>
          <span>{detailState.error}</span>
        </div>
      </DetailModalShell>
    );
  }

  if (!asset) {
    return (
      <DetailModalShell onClose={onClose} onBackdropMouseDown={handleBackdropMouseDown}>
        <div className="state-panel">
          <strong>상세 정보가 없습니다.</strong>
          <span>목록에서 다른 자산을 선택하거나 새로고침해 주세요.</span>
        </div>
      </DetailModalShell>
    );
  }

  return (
    <DetailModalShell onClose={onClose} onBackdropMouseDown={handleBackdropMouseDown}>
      <div className="detail-header">
        <div>
          <p className="eyebrow">Asset detail</p>
          <h2 id="asset-detail-title">{asset.name}</h2>
        </div>
        <div className="detail-actions">
          <button
            type="button"
            className="primary-action"
            onClick={() => {
              setEditError("");
              setIsEditOpen(true);
            }}
            disabled={Boolean(pendingAction)}
          >
            수정
          </button>
          <button
            type="button"
            className="caution-button"
            onClick={handleDispose}
            disabled={asset.status === "폐기" || Boolean(pendingAction)}
          >
            {pendingAction === "dispose" ? "처리 중..." : "폐기 처리"}
          </button>
          <button
            type="button"
            className="danger-button"
            onClick={handleDelete}
            disabled={Boolean(pendingAction)}
          >
            {pendingAction === "delete" ? "삭제 중..." : "삭제"}
          </button>
        </div>
      </div>

      <div className="detail-summary">
        <StatusBadge status={asset.status} />
        <span>ID {asset.id}</span>
      </div>

      <p className="detail-note">삭제한 자산은 목록에서 숨겨지며 변경 이력은 보존됩니다.</p>

      {asset.status === "폐기" && (
        <div className="inline-alert">이미 폐기 상태인 자산입니다.</div>
      )}

      {actionError && <div className="inline-alert action-error">{actionError}</div>}

      <div className="detail-section-heading">
        <h3>기본 정보</h3>
      </div>

      <dl className="detail-grid">
        <DetailItem label="제품명" value={asset.name} />
        <DetailItem label="분류" value={categoryName || formatLookupId(asset.category_id)} />
        <DetailItem
          label="부서(사용자명)"
          value={departmentName || asset.user_name || formatLookupId(asset.department_id)}
        />
        <DetailItem label="위치" value={formatLocation(asset)} />
        <DetailItem label="모델명" value={asset.model_name} />
        <DetailItem label="시리얼번호" value={asset.serial_number} />
        <DetailItem label="구매일" value={asset.purchase_date} />
        <DetailItem label="구매금액" value={formatPrice(asset.purchase_price)} />
        <DetailItem label="사용자명" value={asset.user_name} />
        <DetailItem label="등록일" value={formatDateTime(asset.created_at)} />
        <DetailItem label="수정일" value={formatDateTime(asset.updated_at)} />
        <DetailItem label="메모" value={asset.note} wide />
      </dl>

      <div className="detail-section-heading">
        <h3>사양 이미지</h3>
      </div>

      <div className="asset-spec-image-section">
        {asset.spec_image_url ? (
          <a
            className="asset-spec-image-link"
            href={getUploadUrl(asset.spec_image_url)}
            target="_blank"
            rel="noreferrer"
            aria-label="사양 이미지 확대 보기"
          >
            <img src={getUploadUrl(asset.spec_image_url)} alt="사양 이미지" />
          </a>
        ) : (
          <span>첨부된 사양 이미지가 없습니다.</span>
        )}
      </div>

      <AssetHistory assetId={assetId} refreshKey={historyRefreshKey} />

      <AssetForm
        categories={categories}
        departments={departments}
        lookupError={lookupError}
        isOpen={isEditOpen}
        isSubmitting={isSubmitting}
        error={editError}
        initialAsset={asset}
        title="자산 수정"
        eyebrow="Edit asset"
        submitLabel="수정 저장"
        onClose={() => setIsEditOpen(false)}
        onSubmit={handleSubmitEdit}
      />
    </DetailModalShell>
  );
}

function DetailModalShell({ children, onClose, onBackdropMouseDown }) {
  return (
    <div
      className="detail-modal-backdrop"
      role="presentation"
      onMouseDown={onBackdropMouseDown}
    >
      <section
        className="detail-panel detail-modal"
        aria-label="자산 상세보기"
        role="dialog"
        aria-modal="true"
      >
        <button
          type="button"
          className="icon-button detail-close-button"
          onClick={onClose}
          aria-label="상세보기 닫기"
        >
          ×
        </button>
        {children}
      </section>
    </div>
  );
}

function DetailItem({ label, value, wide = false }) {
  return (
    <div className={wide ? "detail-item detail-item-wide" : "detail-item"}>
      <dt>{label}</dt>
      <dd>{value || "-"}</dd>
    </div>
  );
}

function findLookupName(items, id) {
  if (!id || !Array.isArray(items)) {
    return "";
  }
  return items.find((item) => item.id === id)?.name || "";
}

function formatLookupId(id) {
  return id ? `ID ${id}` : "";
}

function formatPrice(value) {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  return Number(value).toLocaleString("ko-KR");
}

function formatLocation(asset) {
  const group = asset?.location_group || "";
  const detail = asset?.location_detail || "";
  if (group && detail) {
    return `${group} / ${detail}`;
  }
  return group || detail || "";
}

function formatDateTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ko-KR");
}

function getUploadUrl(value) {
  if (!value) {
    return "";
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `${API_BASE_URL}${value}`;
}

export default AssetDetail;
