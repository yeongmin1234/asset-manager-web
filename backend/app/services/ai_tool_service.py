from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from app.models.user import User


class AiToolValidationError(ValueError):
    pass


class AiToolPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    permission: str
    allowed_parameters: Set[str]
    admin_only: bool = False


TOOL_REGISTRY = {
    "inventory_search": ToolDefinition("inventory.search", "dashboard", {"item_code", "keyword", "warehouse_code", "base_date", "limit"}),
    "inventory_low_stock": ToolDefinition("inventory.low_stock", "dashboard", {"keyword", "threshold", "comparison", "limit"}),
    "inventory_compare": ToolDefinition("inventory.compare", "dashboard", {"items"}),
    "inventory_sort": ToolDefinition("inventory.sort", "dashboard", {"direction", "limit"}),
    "inventory_change_compare": ToolDefinition("inventory.change_compare", "dashboard", {"item_code", "keyword", "mode", "direction", "start_at", "end_at", "limit"}),
    "inventory_change_summary": ToolDefinition("inventory.change_summary", "dashboard", {"mode", "today_only", "limit"}),
    "inventory_alert_summary": ToolDefinition("inventory.alert_summary", "dashboard", set()),
    "inventory_out_of_stock": ToolDefinition("inventory.alerts", "dashboard", set()),
    "inventory_alert_negative": ToolDefinition("inventory.alerts", "dashboard", set()),
    "inventory_negative_stock": ToolDefinition("inventory.alerts", "dashboard", set()),
    "inventory_rapid_decrease": ToolDefinition("inventory.alerts", "dashboard", set()),
    "inventory_alert_low_stock": ToolDefinition("inventory.alerts", "dashboard", set()),
    "asset_search": ToolDefinition("asset.search", "assets", {"keyword", "serial_number", "model_name", "limit"}),
    "vehicle_search": ToolDefinition("vehicle.search", "company_cars", {"keyword", "vehicle_number", "limit"}),
}


class AiToolService:
    def validate(self, intent: str, parameters: Optional[Dict[str, Any]], user: Optional[User]):
        tool = TOOL_REGISTRY.get(intent)
        if tool is None:
            raise AiToolValidationError("허용되지 않은 AI 도구입니다.")
        if user is None:
            raise AiToolPermissionError("해당 기능을 사용할 권한이 없습니다.")
        if tool.admin_only and user.role != "admin":
            raise AiToolPermissionError("해당 기능을 사용할 권한이 없습니다.")
        permissions = set(user.menu_permissions or [])
        if user.role != "admin" and tool.permission not in permissions:
            raise AiToolPermissionError("해당 기능을 사용할 권한이 없습니다.")
        cleaned = {}
        for key, value in (parameters or {}).items():
            if key in tool.allowed_parameters and value is not None:
                cleaned[key] = self._clean_value(value)
        return tool, cleaned

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()[:200]
        if isinstance(value, list):
            return [AiToolService._clean_value(item) for item in value[:20]]
        if isinstance(value, (bool, int, float)):
            return value
        return None
