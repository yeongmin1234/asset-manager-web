import logging
from typing import Optional

from app.core.config import Settings, settings
from app.models.user import User
from app.services.ai_intent_service import IntentResult, analyze_intent
from app.services.ai_natural_language_service import NaturalLanguageAiError, NaturalLanguageAiService, contains_prompt_injection
from app.services.ai_tool_service import AiToolPermissionError, AiToolService, AiToolValidationError, TOOL_REGISTRY


logger = logging.getLogger(__name__)


class AiRouterService:
    def __init__(self, config: Settings = settings, natural=None, tools=None):
        self.config = config
        self.natural = natural or NaturalLanguageAiService(config)
        self.tools = tools or AiToolService()

    def route(self, message: str, user: Optional[User] = None):
        rule = analyze_intent(message)
        if contains_prompt_injection(message):
            return rule, "rules", None, False
        if self._is_clear(rule):
            if user is not None and rule.intent in TOOL_REGISTRY:
                self.tools.validate(rule.intent, rule.entities, user)
            return rule, "rules", None, False
        if not self.config.ai_enabled:
            return rule, "rules", None, False
        try:
            raw = self.natural.interpret(message)
            intent = str(raw.get("intent") or "")
            confidence = float(raw.get("confidence") or 0)
            if confidence < float(self.config.ai_min_confidence):
                raise AiToolValidationError("AI confidence is too low")
            tool, parameters = self.tools.validate(intent, raw.get("parameters"), user)
            return IntentResult(intent, rule.normalized_message, parameters, rule.read_only_violation), "natural", tool.name, False
        except AiToolPermissionError:
            raise
        except (NaturalLanguageAiError, AiToolValidationError, TypeError, ValueError):
            logger.info("AI router fallback=true")
            if not self.config.ai_fallback_enabled:
                raise
            return rule, "rules", None, True

    @staticmethod
    def _is_clear(result: IntentResult) -> bool:
        if result.intent == "unknown":
            return False
        if result.intent == "inventory_search":
            keyword = str(result.entities.get("keyword") or "").strip()
            ambiguous = {"", "요즘", "최근", "현재", "오늘", "위험한", "이상한", "확인", "품목"}
            if not result.entities.get("item_code") and keyword in ambiguous:
                return False
        return True
