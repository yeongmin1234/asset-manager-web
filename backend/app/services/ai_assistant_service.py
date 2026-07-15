import logging
import time
from typing import Any, Dict, List, Optional

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
    def process_message(self, message: str) -> Dict[str, Any]:
        started_at = time.monotonic()
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
