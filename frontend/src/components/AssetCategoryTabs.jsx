import React from "react";

function AssetCategoryTabs({
  categories,
  activeCategoryId,
  onSelectCategory,
  onOpenCreate,
  isDisabled = false,
}) {
  const safeCategories = Array.isArray(categories) ? categories : [];

  return (
    <div className="asset-category-tabs" aria-label="자산 분류 탭">
      <div className="asset-category-tabs-heading">
        <strong>분류별 보기</strong>
        <span>목록 하단에서 분류를 빠르게 전환합니다.</span>
      </div>
      <div className="asset-category-tab-row">
        <button
          type="button"
          className={activeCategoryId ? "category-tab" : "category-tab active"}
          onClick={() => onSelectCategory("")}
          disabled={isDisabled}
        >
          전체
        </button>
        {safeCategories.map((category) => (
          <button
            type="button"
            className={
              String(activeCategoryId) === String(category.id)
                ? "category-tab active"
                : "category-tab"
            }
            key={category.id}
            onClick={() => onSelectCategory(String(category.id))}
            disabled={isDisabled}
          >
            {category.name}
          </button>
        ))}
        <button
          type="button"
          className="category-tab category-tab-add"
          onClick={onOpenCreate}
          disabled={isDisabled}
        >
          + 분류 추가
        </button>
      </div>
    </div>
  );
}

export default AssetCategoryTabs;
