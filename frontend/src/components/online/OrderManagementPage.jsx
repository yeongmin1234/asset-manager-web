import React from "react";
import OrderManagementLayout from "./order-management/OrderManagementLayout.jsx";
import OrderDashboardPage from "./order-management/OrderDashboardPage.jsx";
import OrderProcessPage from "./order-management/OrderProcessPage.jsx";
import OrderPreviewPage from "./order-management/OrderPreviewPage.jsx";
import OrderMappingsPage from "./order-management/OrderMappingsPage.jsx";
import OrderHistoryPage from "./order-management/OrderHistoryPage.jsx";
import OrderSettingsPage from "./order-management/OrderSettingsPage.jsx";
import { ORDER_MANAGEMENT_ROUTES } from "./order-management/orderRoutes.js";
import "./online.css";

const PAGES = {
  dashboard: OrderDashboardPage,
  process: OrderProcessPage,
  preview: OrderPreviewPage,
  mappings: OrderMappingsPage,
  history: OrderHistoryPage,
  settings: OrderSettingsPage,
};

function OrderManagementPage({ path = "/online/orders", onNavigate = () => {}, currentUser }) {
  const route = ORDER_MANAGEMENT_ROUTES.find((item) => item.path === path) || ORDER_MANAGEMENT_ROUTES[0];
  const Page = PAGES[route.page];
  return (
    <OrderManagementLayout path={route.path} onNavigate={onNavigate}>
      <Page currentUser={currentUser} />
    </OrderManagementLayout>
  );
}

export default OrderManagementPage;
