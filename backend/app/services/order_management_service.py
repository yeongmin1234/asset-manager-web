"""Response helpers for the order management screens before processing is implemented."""

from app.schemas.order_management import OrderManagementReady


def ready_response() -> OrderManagementReady:
    return OrderManagementReady()
