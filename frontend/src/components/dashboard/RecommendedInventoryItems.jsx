import React from "react";

function RecommendedInventoryItems({ items, disabled, selectedItemCode, onSelect }) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <div className="inventory-recommendations" aria-label="추천 품목">
      <strong>추천 품목</strong>
      <div className="inventory-recommendation-list">
        {items.map((item) => (
          <button
            type="button"
            key={item.item_code}
            disabled={disabled || Boolean(selectedItemCode)}
            className={`inventory-recommendation-item${selectedItemCode === item.item_code ? " selected" : ""}`}
            onClick={() => onSelect(item)}
          >
            <span>{item.item_name || item.item_code}</span>
            <small>{item.item_code}{item.unit ? ` · ${item.unit}` : ""}</small>
          </button>
        ))}
      </div>
    </div>
  );
}

export default RecommendedInventoryItems;
