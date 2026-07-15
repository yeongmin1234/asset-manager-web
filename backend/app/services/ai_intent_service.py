import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


MAX_MESSAGE_LENGTH = 500


@dataclass(frozen=True)
class IntentRule:
    intent: str
    keywords: Tuple[str, ...]
    priority: int
    parser: Optional[str] = None


@dataclass
class IntentResult:
    intent: str
    normalized_message: str
    entities: Dict[str, Any] = field(default_factory=dict)
    read_only_violation: bool = False


INTENT_RULES: List[IntentRule] = sorted(
    [
        IntentRule("inventory_item_code", ("품목코드", "품목 코드"), 100, "item_code"),
        IntentRule("inventory_low_stock", ("재고 부족", "부족 재고", "적게 남은", "이하", "미만"), 90, "threshold"),
        IntentRule("inventory_search", ("재고", "재고량", "남아", "남았", "몇 개", "수량", "현재고", "보유 수량"), 80, "inventory_keyword"),
        IntentRule("vehicle_expiration", ("보험 만료", "리스 만료", "이번 달 보험", "다음 달 보험", "만료 차량"), 70, "period"),
        IntentRule("vehicle_search", ("법인차량", "차량번호", "차량", "자동차"), 60),
        IntentRule("inspection_schedule", ("점검", "만료", "일정"), 50, "period"),
        IntentRule("asset_search", ("자산", "노트북", "모니터", "장비", "시리얼번호", "모델명"), 40),
        IntentRule("help", ("도움말", "사용법", "뭐 할 수 있어", "가능한 기능", "명령어"), 30),
        IntentRule("greeting", ("안녕", "안녕하세요", "반가워", "도와줘"), 20),
    ],
    key=lambda rule: rule.priority,
    reverse=True,
)

READ_ONLY_BLOCK_KEYWORDS = (
    "삭제", "등록", "추가", "수정", "변경", "저장", "생성", "권한", "실행", "재시작",
)
PERIOD_PATTERNS = (
    ("다음 달", "next_month"),
    ("이번 달", "this_month"),
    ("이번 주", "this_week"),
    ("오늘", "today"),
    ("7일 이내", "within_7_days"),
    ("30일 이내", "within_30_days"),
)


def normalize_message(message: str) -> str:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("질문을 입력해주세요.")
    normalized = re.sub(r"\s+", " ", message.strip()).lower()
    if len(normalized) > MAX_MESSAGE_LENGTH:
        raise ValueError("질문은 500자 이하로 입력해주세요.")
    normalized = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.#+:/-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def analyze_intent(message: str) -> IntentResult:
    normalized = normalize_message(message)
    read_only_violation = any(keyword in normalized for keyword in READ_ONLY_BLOCK_KEYWORDS)
    for rule in INTENT_RULES:
        if any(keyword in normalized for keyword in rule.keywords):
            entities = _parse_entities(rule.parser, normalized)
            return IntentResult(rule.intent, normalized, entities, read_only_violation)
    return IntentResult("unknown", normalized, {}, read_only_violation)


def _parse_entities(parser: Optional[str], message: str) -> Dict[str, Any]:
    if parser == "threshold":
        match = re.search(r"(\d+)\s*개?\s*(이하|미만)", message)
        return {
            "threshold": int(match.group(1)) if match else 10,
            "comparison": match.group(2) if match else "이하",
        }
    if parser == "item_code":
        match = re.search(r"품목\s*코드\s*[:#]?\s*([a-z0-9][a-z0-9._-]*)", message, re.IGNORECASE)
        return {"item_code": match.group(1).upper()} if match else {}
    if parser == "period":
        for phrase, value in PERIOD_PATTERNS:
            if phrase in message:
                return {"period": value}
        return {}
    if parser == "inventory_keyword":
        keyword = re.split(r"재고|재고량|현재고|보유 수량|수량|남아|남았|몇 개", message, maxsplit=1)[0]
        keyword = re.sub(r"(알려줘|조회|보여줘|확인|해줘)$", "", keyword).strip()
        return {"keyword": keyword} if keyword else {}
    return {}
