import copy
import logging
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from app.services.ai_inventory_context_service import (
    classify_inventory_followup,
    context_from_item,
    get_inventory_context,
    save_inventory_context,
    sanitize_client_context,
    select_context_item,
)
from app.services.ai_intent_service import IntentResult, analyze_intent
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import InventoryError, InventoryRateLimitError, InventoryService
from app.services.product_match_service import normalize_product_text


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
_CONTEXT_UNSET = object()


class AiAssistantPermissionError(PermissionError):
    pass


class AiAssistantService:
    def __init__(self, inventory_service=None):
        self.inventory_service = inventory_service

    def process_message(self, message: str, user_id: Optional[int] = None, user=None, context=_CONTEXT_UNSET) -> Dict[str, Any]:
        started_at = time.monotonic()
        has_client_context = context is not _CONTEXT_UNSET
        client_context = sanitize_client_context(context) if has_client_context else None
        followup_intent = classify_inventory_followup(message)
        if followup_intent and (has_client_context or user_id is not None):
            self._ensure_permission("inventory_search", user)
            legacy_intent = (
                "inventory_context_total"
                if not has_client_context and followup_intent == "inventory_total_followup"
                else followup_intent
            )
            response = self._build_client_context_response(
                message, followup_intent, client_context,
            ) if has_client_context else self._build_context_response(user_id, legacy_intent)
            logger.info(
                "AI assistant processed intent=%s success=true response_time_ms=%s",
                response.get("intent") or followup_intent,
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
                "'{}'와 일치하거나 비슷한 품목을 찾지 못했습니다.".format(candidate),
                recommendation,
                INVENTORY_SUGGESTIONS,
            )
        match_type = recommendation.get("match_type")
        if match_type is None and recommendation["total"] == 1:
            only = items[0]
            if str(only.get("item_code") or "").strip().casefold() == candidate.casefold():
                match_type = "exact_code"
            elif normalize_product_text(only.get("item_name"), compact=True) == normalize_product_text(candidate, compact=True):
                match_type = "space_normalized"
        if recommendation["total"] == 1 and match_type in {
            "exact_code", "exact_name", "space_normalized",
        }:
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
        if match_type == "fuzzy":
            message_text = "'{}'과 비슷한 품목입니다.\n조회할 품목을 선택해주세요.".format(candidate)
        elif match_type == "code_prefix":
            message_text = "입력한 품목코드와 정확히 일치하는 품목이 없습니다.\n비슷한 코드의 품목을 선택해주세요."
        else:
            message_text = "'{}'와 일치하는 품목이 여러 개입니다.\n조회할 품목을 선택해주세요.".format(candidate)
        if recommendation["has_more"]:
            message_text += "\n'{}'와 일치하는 품목이 많습니다. 품목명을 조금 더 구체적으로 입력해주세요.".format(candidate)
        response = self._response(
            "inventory_recommendation", message_text, recommendation, INVENTORY_SUGGESTIONS,
        )
        response["context"] = {
            "selected_item_code": None, "selected_item_name": None, "unit": None, "size": None,
            "last_intent": "inventory_recommendation", "searched_at": None,
            "last_warehouse_filter": None, "search_keyword": candidate,
            "product_candidates": recommendation["items"][:8], "inventory_result": None,
        }
        return response

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
        response = self._response(result.intent, message, data, INVENTORY_SUGGESTIONS)
        if len(items) == 1:
            response["context"] = context_from_item(
                items[0], result.intent, datetime.now(timezone.utc).isoformat(),
            )
        return response

    def _build_client_context_response(self, message, intent, context):
        if intent == "context_clear":
            return self._response(intent, "대화 문맥을 초기화했습니다. 새 품목을 조회해주세요.", None, INVENTORY_SUGGESTIONS)
        if not context or not context.get("selected_item_code"):
            response = self._response(
                intent, "먼저 조회할 품목을 선택하거나 품목명·품목코드를 입력해주세요.",
                {"type": "context_missing"}, INVENTORY_SUGGESTIONS,
            )
            response["context"] = None
            return response
        item_name = context.get("selected_item_name") or context["selected_item_code"]
        inventory = context.get("inventory_result") or {}
        warehouses = inventory.get("warehouses") or []
        next_context = copy.deepcopy(context)
        next_context["last_intent"] = intent

        if intent == "inventory_refresh":
            result = IntentResult("inventory_search", "", {"item_code": context["selected_item_code"]})
            response = self._execute_inventory_query(result, None)
            response["intent"] = "inventory_refresh"
            if response.get("context"):
                response["context"]["last_intent"] = "inventory_refresh"
            return response
        if intent == "inventory_warehouse_filter":
            normalized = re.sub(r"\s+", " ", message.strip().lower())
            keyword = re.sub(r"(?:관련\s*)?창고|만|보여줘|알려줘|조회해줘", "", normalized).strip()
            if keyword == "해당" and context.get("last_warehouse_filter"):
                keyword = context["last_warehouse_filter"]
            filtered = [row for row in warehouses if keyword.casefold() in str(row.get("warehouse_name") or "").casefold()]
            next_context["last_warehouse_filter"] = keyword
            if not filtered:
                response = self._response(intent, "직전 조회 결과에서 '{}'와 일치하는 창고를 찾지 못했습니다.".format(keyword), {"type": "inventory_result", "inventory_response": self._inventory_payload([], item_name, context)}, INVENTORY_SUGGESTIONS)
            else:
                total = self._sum_quantities(filtered)
                response = self._response(intent, "{}의 {} 관련 창고 재고는 총 {}개입니다.".format(item_name, keyword, self._format_quantity(total)), {"type": "inventory_result", "inventory_response": self._inventory_payload(filtered, item_name, context), "selected_item_code": context["selected_item_code"]}, INVENTORY_SUGGESTIONS)
        elif intent == "inventory_other_warehouses":
            excluded = context.get("last_warehouse_filter")
            if not excluded:
                response = self._response(intent, "어느 창고를 제외할지 먼저 알려주세요.", None, INVENTORY_SUGGESTIONS)
            else:
                filtered = [row for row in warehouses if excluded.casefold() not in str(row.get("warehouse_name") or "").casefold()]
                response = self._response(intent, "{}의 나머지 창고 재고를 표시합니다.".format(item_name), {"type": "inventory_result", "inventory_response": self._inventory_payload(filtered, item_name, context), "selected_item_code": context["selected_item_code"]}, INVENTORY_SUGGESTIONS)
        elif intent in ("inventory_show_all_warehouses", "inventory_context_warehouses"):
            response = self._response(intent, "{}의 창고별 재고를 표시합니다.".format(item_name), {"type": "inventory_result", "inventory_response": self._inventory_payload(warehouses, item_name, context), "selected_item_code": context["selected_item_code"]}, INVENTORY_SUGGESTIONS)
        elif intent in ("inventory_total_followup", "inventory_context_total"):
            response = self._response(intent, "{}의 현재 총재고는 {}개입니다.".format(item_name, self._format_quantity(inventory.get("total_quantity"))), None, INVENTORY_SUGGESTIONS)
        elif intent == "inventory_item_code_followup":
            response = self._response(intent, "{}의 품목코드는 {}입니다.".format(item_name, context["selected_item_code"]), None, INVENTORY_SUGGESTIONS)
        elif intent == "inventory_item_name_followup":
            response = self._response(intent, "선택한 품목명은 {}입니다.".format(item_name), None, INVENTORY_SUGGESTIONS)
        elif intent == "inventory_unit_followup":
            response = self._response(intent, "{}의 단위는 {}입니다.".format(item_name, context.get("unit") or "확인할 수 없음"), None, INVENTORY_SUGGESTIONS)
        elif intent == "inventory_size_followup":
            response = self._response(intent, "{}의 규격은 {}입니다.".format(item_name, context.get("size") or "확인할 수 없음"), None, INVENTORY_SUGGESTIONS)
        else:
            response = self._response(intent, self._item_summary({"item_name": item_name, "total_quantity": inventory.get("total_quantity")}), None, INVENTORY_SUGGESTIONS)
        response["context"] = next_context
        return response

    @staticmethod
    def _inventory_payload(warehouses, item_name, context):
        return {"success": True, "authenticated": True, "total": 1, "items": [{"item_code": context["selected_item_code"], "item_name": item_name, "size": context.get("size"), "unit": context.get("unit"), "total_quantity": str(AiAssistantService._sum_quantities(warehouses)), "warehouses": warehouses}], "message": "직전 재고 조회 결과입니다.", "response_time_ms": 0}

    @staticmethod
    def _sum_quantities(warehouses):
        total = Decimal("0")
        for row in warehouses:
            try:
                total += Decimal(str(row.get("quantity") or "0"))
            except (InvalidOperation, ValueError):
                continue
        return total

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
