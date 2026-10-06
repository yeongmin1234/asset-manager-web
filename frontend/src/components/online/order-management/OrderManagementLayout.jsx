import React from "react";
import { ORDER_MANAGEMENT_ROUTES } from "./orderRoutes.js";

function OrderManagementLayout({ path, onNavigate, children }) {
  return (
    <div className="online-page online-order-page">
      <div className="portal-screen-heading">
        <h2>발주 관리</h2>
        <p>온라인 TEAM 발주 업무를 관리합니다.</p>
      </div>
      <nav className="online-order-nav" aria-label="발주 관리 화면">
        {ORDER_MANAGEMENT_ROUTES.map((route) => (
          <button type="button" key={route.path}
            className={path === route.path ? "online-order-nav-item is-active" : "online-order-nav-item"}
            aria-current={path === route.path ? "page" : undefined}
            onClick={() => onNavigate(route.path)}>
            {route.label}
          </button>
        ))}
      </nav>
      {children}
    </div>
  );
}

export default OrderManagementLayout;
