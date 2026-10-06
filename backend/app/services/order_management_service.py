"""Response helpers for the order management screens before processing is implemented."""

from app.schemas.order_management import OrderDashboardResponse, OrderListResponse, OrderManagementReady


def ready_response() -> OrderManagementReady:
    return OrderManagementReady()


def empty_dashboard() -> OrderDashboardResponse:
    return OrderDashboardResponse()


def empty_list() -> OrderListResponse:
    return OrderListResponse()
