import logging
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from app.services.ai_inventory_context_service import (
    classify_inventory_followup,
    get_inventory_context,
    save_inventory_context,
    select_context_item,
)
from app.services.ai_intent_service import IntentResult, analyze_intent
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import InventoryError, InventoryRateLimitError, InventoryService


logger = logging.getLogger(__name__)

DEFAULT_SUGGESTIONS = [
    "품목명으로 재고 조회",
    "품목코드로 재고 조회",
    "창고별 재고 조회",
]
INVENTORY_SUGGESTIONS = [
    "품목명으로 재고 조회",
    "품목코드로 재고 조회",
    "창고별 재고 조회",
]


class AiAssistantPermissionError(PermissionError):
    pass


class AiAssistantService:
    def __init__(self, inventory_service=None):
        self.inventory_service = inventory_service

    def process_message(self, message: str, user_id: Optional[int] = None, user=None) -> Dict[str, Any]:
        started_at = time.monotonic()
        followup_intent = classify_inventory_followup(message)
        if followup_intent and user_id is not None:
            self._ensure_permission("inventory_search", user)
            response = self._build_context_response(user_id, followup_intent)
            logger.info(
                "AI assistant processed intent=%s success=true response_time_ms=%s",
                followup_intent,
                max(0, int((time.monotonic() - started_at) * 1000)),
            )
            return response
        result = analyze_intent(message)
        if not result.read_only_violation and result.intent in {"unknown", "inventory_search"}:
            resolved = self._resolve_inventory_products(result, message, user_id, user)
            if isinstance(resolved, dict):
                logger.info(
                    "AI assistant processed intent=%s success=true response_time_ms=%s",
                    resolved.get("intent") or "inventory_recommendation",
                    max(0, int((time.monotonic() - started_at) * 1000)),
                )
                return resolved
            result = resolved
        self._ensure_permission(result.intent, user)
        try:
            response = self._build_response(result, user_id)
            logger.info(
                "AI assistant processed intent=%s success=true response_time_ms=%s",
                result.intent,
                max(0, int((time.monotonic() - started_at) * 1000)),
            )
            return response
        except Exception as exc:
            logger.warning(
                "AI assistant failed intent=%s error_type=%s response_time_ms=%s",
                result.intent,
                type(exc).__name__,
                max(0, int((time.monotonic() - started_at) * 1000)),
            )
            raise

    def _resolve_inventory_products(self, result, message, user_id, user):
        candidate = str(result.entities.get("keyword") or (message or "").strip()).strip()
        if not candidate or len(candidate) > 40:
            return result

        # Previously returned inventory is authoritative and needs no ECOUNT call.
        context = get_inventory_context(user_id) if user_id is not None else None
        if context:
            normalized = candidate.casefold()
            for item in context.last_inventory_items:
                if normalized in {
                    str(item.get("item_name") or "").strip().casefold(),
                    str(item.get("item_code") or "").strip().casefold(),
                }:
                    return IntentResult(
                        "inventory_search", result.normalized_message,
                        {"item_code": item["item_code"]},
                        result.read_only_violation,
                    )

        # Only a short, sentence-free token is eligible for exact product-name
        # verification. General sentences remain unknown and make no API call.
        if result.intent == "unknown" and not re.fullmatch(r"[가-힣A-Za-z0-9._()/-]{2,40}", candidate):
            return result
        self._ensure_permission("inventory_search", user)
        service = self.inventory_service or InventoryService()
        try:
            recommendation = service.recommend_products(candidate, limit=8)
        except InventoryRateLimitError:
            raise
        except (InventoryError, EcountConfigurationError, ValueError):
            if result.intent == "unknown":
                return result
            raise
        recommendation = dict(recommendation)
        items = recommendation["items"]
        logger.info(
            "AI inventory candidate search intent=%s product_search_cache_hit=%s candidate_count=%s external_inventory_call=false",
            result.intent,
            str(bool(recommendation.get("cache_hit"))).lower(),
            recommendation.get("total", len(items)),
        )
        if not items:
            if result.intent == "unknown":
                return result
            recommendation["type"] = "product_not_found"
            return self._response(
                "inventory_recommendation",
                "검색 조건에 맞는 품목이 없습니다.",
                recommendation,
                INVENTORY_SUGGESTIONS,
            )
        if recommendation["total"] == 1:
            return IntentResult(
                "inventory_search", result.normalized_message,
                {
                    "item_code": items[0]["item_code"],
                    "_resolved_product": items[0],
                    "_product_search_cache_hit": bool(recommendation.get("cache_hit")),
                },
                result.read_only_violation,
            )
        recommendation["type"] = "product_candidates"
        message_text = "'{}'와 일치하는 품목이 여러 개입니다.\n조회할 품목을 선택해주세요.".format(candidate)
        if recommendation["has_more"]:
            message_text += "\n'{}'와 일치하는 품목이 많습니다. 품목명을 조금 더 구체적으로 입력해주세요.".format(candidate)
        return self._response(
            "inventory_recommendation", message_text, recommendation, INVENTORY_SUGGESTIONS,
        )

    @staticmethod
    def _ensure_permission(intent: str, user) -> None:
        if user is None or user.role == "admin":
            return
        permission = (
            "dashboard" if intent.startswith("inventory_")
            else "assets" if intent == "asset_search"
            else "company_cars" if intent.startswith("vehicle_")
            else None
        )
        if permission and permission not in set(user.menu_permissions or []):
            raise AiAssistantPermissionError("해당 기능을 사용할 권한이 없습니다.")
    def _build_response(self, result: IntentResult, user_id: Optional[int] = None) -> Dict[str, Any]:
        if result.read_only_violation:
            return self._response(
                result.intent,
                "현재 AI 업무 도우미는 조회 기능만 지원합니다.",
                result.entities,
                DEFAULT_SUGGESTIONS,
            )

        if result.intent in {"inventory_search", "inventory_item_code"}:
            return self._execute_inventory_query(result, user_id)

        if result.intent == "inventory_low_stock":
            data = dict(result.entities)
            data["type"] = "feature_disabled"
            return self._response(
                result.intent,
                "현재 부족 재고 전체 조회 기능은 안정화를 위해 일시 중지되었습니다.\n품목명 또는 품목코드로 재고를 조회해주세요.",
                data,
                INVENTORY_SUGGESTIONS,
            )

        handlers = {
            "inventory_alert_summary": self._inventory_pending,
            "inventory_out_of_stock": self._inventory_pending,
            "inventory_alert_negative": self._inventory_pending,
            "inventory_rapid_decrease": self._inventory_pending,
            "inventory_alert_low_stock": self._inventory_pending,
            "inventory_compare": self._inventory_pending,
            "inventory_sort": self._inventory_pending,
            "inventory_filter": self._inventory_pending,
            "inventory_min": self._inventory_pending,
            "inventory_max": self._inventory_pending,
            "inventory_zero": self._inventory_pending,
            "inventory_negative": self._inventory_pending,
            "inventory_change_summary": self._inventory_pending,
            "inventory_change_compare": self._inventory_pending,
            "inventory_increased": self._inventory_pending,
            "inventory_decreased": self._inventory_pending,
            "inventory_largest_increase": self._inventory_pending,
            "inventory_largest_decrease": self._inventory_pending,
            "inventory_history_compare": self._inventory_pending,
            "asset_search": lambda _: "자산 조회 기능은 추후 연결 예정입니다.",
            "vehicle_search": lambda _: "차량 정보 조회 기능은 추후 연결 예정입니다.",
            "vehicle_expiration": lambda _: "보험·리스 만료 조회 기능은 추후 연결 예정입니다.",
            "inspection_schedule": lambda _: "점검·만료 일정 조회 기능은 추후 연결 예정입니다.",
            "greeting": lambda _: "안녕하세요. 재고, 자산, 차량, 점검 일정 조회를 도와드릴 수 있습니다.",
            "help": lambda _: (
                "현재 지원하거나 준비 중인 기능입니다.\n\n"
                "• 품목명 재고 조회\n• 품목코드 재고 조회\n• 창고별 재고 조회\n"
                "• 자산 조회\n• 차량 정보 조회\n• 보험·리스 만료 조회\n• 점검 일정 조회"
            ),
            "unknown": lambda _: "아직 해당 질문은 처리할 수 없습니다. 재고, 자산, 차량 또는 점검 일정에 대해 질문해주세요.",
        }
        message = handlers[result.intent](result)
        suggestions = INVENTORY_SUGGESTIONS if result.intent.startswith("inventory_") else DEFAULT_SUGGESTIONS
        return self._response(result.intent, message, result.entities, suggestions)

    def _execute_inventory_query(
        self, result: IntentResult, user_id: Optional[int],
    ) -> Dict[str, Any]:
        service = self.inventory_service or InventoryService()
        item_code = str(result.entities.get("item_code") or "").strip().upper()
        keyword = str(result.entities.get("keyword") or "").strip()
        threshold = result.entities.get("threshold", 10)
        resolved_product = result.entities.get("_resolved_product")

        if result.intent == "inventory_item_code" and not item_code:
            return self._response(
                result.intent,
                "조회할 품목코드를 함께 입력해주세요.",
                result.entities,
                INVENTORY_SUGGESTIONS,
            )

        if item_code:
            logger.info(
                "AI inventory lookup intent=%s product_search_cache_hit=%s candidate_count=1 external_inventory_call=true",
                result.intent,
                str(bool(result.entities.get("_product_search_cache_hit"))).lower(),
            )
            inventory_response = service.get_aggregated_inventory(item_code, product=resolved_product)
        elif keyword:
            logger.info(
                "AI inventory lookup intent=%s product_search_cache_hit=false candidate_count=- external_inventory_call=true",
                result.intent,
            )
            inventory_response = service.search_inventory_by_keyword(keyword, limit=20)
        else:
            return self._response(
                result.intent,
                "조회할 품목명 또는 품목코드를 함께 입력해주세요.",
                result.entities,
                INVENTORY_SUGGESTIONS,
            )

        items = inventory_response.get("items") or []
        if items and user_id is not None:
            save_inventory_context(
                user_id=user_id,
                intent=result.intent,
                query=keyword or item_code,
                items=items,
                threshold=int(threshold) if result.intent == "inventory_low_stock" else None,
                searched_at=datetime.now(timezone.utc).isoformat(),
                selected_item_code=items[0].get("item_code") if len(items) == 1 else None,
            )

        message = self._build_inventory_message(result.intent, inventory_response, threshold)
        data = {
            key: value for key, value in result.entities.items()
            if not str(key).startswith("_")
        }
        data.update({
            "type": "inventory_result",
            "inventory_response": inventory_response,
            "selected_item_code": items[0].get("item_code") if len(items) == 1 else None,
            "base_date": InventoryService._korea_today(),
        })
        return self._response(result.intent, message, data, INVENTORY_SUGGESTIONS)

    def _build_inventory_message(
        self, intent: str, inventory_response: Dict[str, Any], threshold: Any,
    ) -> str:
        items = inventory_response.get("items") or []
        if intent == "inventory_low_stock":
            if not items:
                return "재고 {}개 이하인 품목이 없습니다.".format(self._format_quantity(threshold))
            return (
                "재고 {}개 이하 품목은 {}개입니다.\n"
                "상세 결과는 왼쪽 재고 조회 결과에서 확인할 수 있습니다."
            ).format(self._format_quantity(threshold), len(items))
        if not items:
            return "검색 조건에 맞는 품목을 찾지 못했습니다."
        if len(items) > 1:
            return (
                "검색된 품목은 {}개입니다.\n"
                "상세 결과는 왼쪽 재고 조회 결과에서 확인할 수 있습니다."
            ).format(len(items))

        item = items[0]
        name = item.get("item_name") or item.get("item_code")
        code = item.get("item_code")
        label = "{}({})".format(name, code) if item.get("item_name") and code else name
        warehouses = item.get("warehouses") or []
        if not warehouses:
            return "{}의 재고 정보가 없습니다.".format(label)
        lines = [
            "{}의 현재 재고는 총 {}개입니다.".format(
                label, self._format_quantity(item.get("total_quantity")),
            )
        ]
        lines.extend(
            "• {}: {}개".format(
                warehouse.get("warehouse_name") or warehouse.get("warehouse_code") or "창고",
                self._format_quantity(warehouse.get("quantity")),
            )
            for warehouse in warehouses
        )
        return "\n".join(lines)

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
        return "요청 조건에 따라 재고 데이터를 조회·분석하겠습니다."

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
