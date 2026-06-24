import React, { useEffect, useMemo, useState } from "react";

const CHECKLIST_STORAGE_KEY = "assetManager.installLibraryChecklist";

function InstallChecklistPanel({ items = [] }) {
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

  return (
    <section className="install-checklist-panel">
      <div className="install-checklist-heading">
        <div>
          <h3>설치 체크리스트</h3>
          <p>필수 자료와 설치 순서가 있는 자료를 브라우저별로 체크합니다.</p>
        </div>
        <span>{completedCount}/{requiredItems.length}</span>
      </div>
      {requiredItems.length === 0 ? (
        <p className="install-checklist-empty">필수 설치 항목이 없습니다.</p>
      ) : (
        <div className="install-checklist-list">
          {requiredItems.map((item) => (
            <label key={item.id} className="install-checklist-item">
              <input
                type="checkbox"
                checked={checkedMap[String(item.id)] === true}
                onChange={(event) =>
                  setCheckedMap((current) => ({
                    ...current,
                    [String(item.id)]: event.target.checked,
                  }))
                }
              />
              <span>
                <strong>{item.title}</strong>
                <small>{Number(item.install_order || 0) > 0 ? `${item.install_order}순서` : "필수"}</small>
              </span>
            </label>
          ))}
        </div>
      )}
      <button type="button" className="secondary-button" onClick={() => setCheckedMap({})}>
        체크 초기화
      </button>
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
