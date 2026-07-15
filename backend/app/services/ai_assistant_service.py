import logging
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from app.services.ai_inventory_context_service import (
    classify_inventory_followup,
    get_inventory_context,
    select_context_item,
)
from app.services.ai_intent_service import IntentResult, analyze_intent


logger = logging.getLogger(__name__)

DEFAULT_SUGGESTIONS = [
    "벤틀리 재고 알려줘",
    "재고 10개 이하 품목 보여줘",
    "이번 달 보험 만료 차량 알려줘",
]
INVENTORY_SUGGESTIONS = [
    "재고 10개 이하 품목 보여줘",
    "품목코드로 재고 조회",
]


class AiAssistantService:
    def process_message(self, message: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        started_at = time.monotonic()
        followup_intent = classify_inventory_followup(message)
        if followup_intent and user_id is not None:
            response = self._build_context_response(user_id, followup_intent)
            logger.info(
                "AI assistant processed intent=%s success=true response_time_ms=%s",
                followup_intent,
                max(0, int((time.monotonic() - started_at) * 1000)),
            )
            return response
        result = analyze_intent(message)
        try:
            response = self._build_response(result)
            logger.info(
                "AI assistant processed intent=%s success=true response_time_ms=%s",
                result.intent,
                max(0, int((time.monotonic() - started_at) * 1000)),
            )
            return response
        except Exception:
            logger.exception("AI assistant failed intent=%s", result.intent)
            raise

    def _build_response(self, result: IntentResult) -> Dict[str, Any]:
        if result.read_only_violation:
            return self._response(
                result.intent,
                "현재 AI 업무 도우미는 조회 기능만 지원합니다.",
                result.entities,
                DEFAULT_SUGGESTIONS,
            )

        handlers = {
            "inventory_item_code": self._inventory_item_code,
            "inventory_low_stock": self._inventory_pending,
            "inventory_search": self._inventory_pending,
            "asset_search": lambda _: "자산 조회 기능은 추후 연결 예정입니다.",
            "vehicle_search": lambda _: "차량 정보 조회 기능은 추후 연결 예정입니다.",
            "vehicle_expiration": lambda _: "보험·리스 만료 조회 기능은 추후 연결 예정입니다.",
            "inspection_schedule": lambda _: "점검·만료 일정 조회 기능은 추후 연결 예정입니다.",
            "greeting": lambda _: "안녕하세요. 재고, 자산, 차량, 점검 일정 조회를 도와드릴 수 있습니다.",
            "help": lambda _: (
                "현재 지원하거나 준비 중인 기능입니다.\n\n"
                "• 재고 조회\n• 부족 재고 조회\n• 품목코드 재고 조회\n"
                "• 자산 조회\n• 차량 정보 조회\n• 보험·리스 만료 조회\n• 점검 일정 조회"
            ),
            "unknown": lambda _: "아직 해당 질문은 처리할 수 없습니다. 재고, 자산, 차량 또는 점검 일정에 대해 질문해주세요.",
        }
        message = handlers[result.intent](result)
        suggestions = INVENTORY_SUGGESTIONS if result.intent.startswith("inventory_") else DEFAULT_SUGGESTIONS
        return self._response(result.intent, message, result.entities, suggestions)

    def _build_context_response(self, user_id: int, intent: str) -> Dict[str, Any]:
        context = get_inventory_context(user_id)
        if context is None or not context.last_inventory_items:
            return self._response(
                intent,
                "최근 조회한 재고 정보가 없습니다.\n품목명 또는 품목코드로 먼저 재고를 조회해 주세요.",
                None,
                INVENTORY_SUGGESTIONS,
            )

        if intent == "inventory_refresh":
            return self._response(
                intent,
                "최신 재고 정보를 다시 조회하겠습니다.",
                {
                    "item_code": context.last_item_code,
                    "keyword": context.last_item_name,
                    "threshold": context.last_threshold,
                    "source_intent": context.last_intent,
                },
                INVENTORY_SUGGESTIONS,
            )

        item = context.last_selected_item or context.last_inventory_items[0]
        if intent in ("inventory_context_first", "inventory_context_second"):
            index = 0 if intent.endswith("first") else 1
            if index >= len(context.last_inventory_items):
                message = "해당 순서의 품목이 최근 검색 결과에 없습니다."
            else:
                item = context.last_inventory_items[index]
                select_context_item(user_id, item)
                message = self._item_summary(item)
        elif intent == "inventory_context_lowest":
            item = min(context.last_inventory_items, key=self._quantity_for_sort)
            select_context_item(user_id, item)
            message = "가장 재고가 적은 품목은 {}입니다. 현재 총재고는 {}개입니다.".format(
                item.get("item_name") or item.get("item_code"), self._format_quantity(item.get("total_quantity")),
            )
        elif intent == "inventory_context_warehouses":
            warehouses = item.get("warehouses") or []
            message = (
                ", ".join(
                    "{} {}개".format(
                        warehouse.get("warehouse_name") or warehouse.get("warehouse_code") or "창고",
                        self._format_quantity(warehouse.get("quantity")),
                    )
                    for warehouse in warehouses
                ) + "입니다."
                if warehouses
                else "등록된 창고별 재고가 없습니다."
            )
        elif intent == "inventory_context_total":
            message = "현재 총재고는 {}개입니다.".format(self._format_quantity(item.get("total_quantity")))
        else:
            message = self._item_summary(item)

        inventory_response = {
            "success": True,
            "authenticated": True,
            "total": len(context.last_inventory_items),
            "items": context.last_inventory_items,
            "message": "최근 재고 조회 결과입니다.",
            "response_time_ms": 0,
        }
        return self._response(
            intent,
            message,
            {"inventory_response": inventory_response, "selected_item_code": item.get("item_code")},
            INVENTORY_SUGGESTIONS,
        )

    def _item_summary(self, item: Dict[str, Any]) -> str:
        return "{}의 현재 총재고는 {}개입니다.".format(
            item.get("item_name") or item.get("item_code"), self._format_quantity(item.get("total_quantity")),
        )

    @staticmethod
    def _quantity_for_sort(item: Dict[str, Any]) -> Decimal:
        try:
            return Decimal(str(item.get("total_quantity")))
        except (InvalidOperation, ValueError):
            return Decimal("Infinity")

    @staticmethod
    def _format_quantity(value: Any) -> str:
        raw = str(value if value is not None else "").strip()
        if "." in raw:
            raw = raw.rstrip("0").rstrip(".")
        return raw or "확인 필요"

    @staticmethod
    def _inventory_pending(_: IntentResult) -> str:
        # Phase 2 integration point: call inventory_service here.
        return "현재 재고 조회 기능을 연결 중입니다. 이카운트 재고 API 연결 후 조회할 수 있습니다."

    @staticmethod
    def _inventory_item_code(result: IntentResult) -> str:
        if not result.entities.get("item_code"):
            return "조회할 품목코드를 함께 입력해주세요."
        return AiAssistantService._inventory_pending(result)

    @staticmethod
    def _response(
        intent: str,
        message: str,
        data: Optional[Dict[str, Any]],
        suggestions: List[str],
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "intent": intent,
            "message": message,
            "data": data or None,
            "suggestions": suggestions,
        }
