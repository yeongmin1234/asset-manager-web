import React, { useEffect, useMemo, useState } from "react";

const CHECKLIST_STORAGE_KEY = "assetManager.installLibraryChecklist";

function InstallChecklistPanel({ items = [], onDownload }) {
  const requiredItems = useMemo(
    () =>
      items
        .filter((item) => item.is_required || Number(item.install_order || 0) > 0)
        .sort((left, right) => Number(left.install_order || 0) - Number(right.install_order || 0)),
    [items],
  );
  const [checkedMap, setCheckedMap] = useState(() => loadChecklist());

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(checkedMap));
    }
  }, [checkedMap]);

  const completedCount = requiredItems.filter((item) => checkedMap[String(item.id)]).length;
  const progressPercent =
    requiredItems.length > 0 ? Math.round((completedCount / requiredItems.length) * 100) : 0;

  return (
    <section className="install-checklist-panel">
      <div className="install-checklist-heading">
        <div>
          <h3>설치 체크리스트</h3>
          <p>필수 자료와 설치 순서가 있는 자료를 브라우저별로 체크합니다.</p>
        </div>
        <div className="install-checklist-progress">
          <strong>{completedCount}/{requiredItems.length}</strong>
          <span>{progressPercent}%</span>
        </div>
      </div>
      <div className="install-checklist-progress-bar" aria-hidden="true">
        <span style={{ width: `${progressPercent}%` }} />
      </div>
      {requiredItems.length === 0 ? (
        <p className="install-checklist-empty">필수 설치 항목이 없습니다.</p>
      ) : (
        <div className="install-checklist-list">
          {requiredItems.map((item) => (
            <article
              key={item.id}
              className={
                checkedMap[String(item.id)] === true
                  ? "install-checklist-item completed"
                  : "install-checklist-item"
              }
            >
              <input
                className="install-checklist-checkbox"
                type="checkbox"
                aria-label={`${item.title} 설치 완료`}
                checked={checkedMap[String(item.id)] === true}
                onChange={(event) =>
                  setCheckedMap((current) => ({
                    ...current,
                    [String(item.id)]: event.target.checked,
                  }))
                }
              />
              <div className="install-checklist-main">
                <div className="install-checklist-title-row">
                  {Number(item.install_order || 0) > 0 && (
                    <em className="install-library-order-badge">{item.install_order}</em>
                  )}
                  <strong title={item.title}>{item.title}</strong>
                  {item.is_required && <em className="install-library-required-badge">필수</em>}
                  {item.version && <small>{item.version}</small>}
                </div>
                <small
                  className="install-checklist-meta"
                  title={`${item.category || "기타"} / ${item.original_filename || item.description || "-"}`}
                >
                  {item.category || "기타"} / {item.original_filename || item.description || "-"}
                </small>
              </div>
              {checkedMap[String(item.id)] === true ? (
                <span className="install-checklist-complete-badge">설치 완료</span>
              ) : (
                <button
                  type="button"
                  className="secondary-button install-checklist-download"
                  onClick={() => onDownload?.(item)}
                >
                  다운로드
                </button>
              )}
            </article>
          ))}
        </div>
      )}
      <div className="install-checklist-footer">
        <button type="button" className="secondary-button" onClick={() => setCheckedMap({})}>
          체크 초기화
        </button>
      </div>
    </section>
  );
}

function loadChecklist() {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const storedValue = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
    return storedValue ? JSON.parse(storedValue) : {};
  } catch {
    return {};
  }
}

export default InstallChecklistPanel;
