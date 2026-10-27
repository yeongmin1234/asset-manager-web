import React, { useEffect } from "react";
import { createPortal } from "react-dom";
import WarehouseInventoryList from "./WarehouseInventoryList";
export default function WarehouseInventoryModal({ rows, unit, onClose }) {
  useEffect(() => { const key = (e) => e.key === "Escape" && onClose(); window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); }, [onClose]);
  return createPortal(<div className="ai-modal-layer"><section className="ai-modal"><header><h2>전체 창고 재고</h2><button type="button" onClick={onClose}>닫기</button></header><div className="ai-modal-list"><WarehouseInventoryList rows={rows} unit={unit} /></div></section></div>, document.body);
}
