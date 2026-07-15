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
        IntentRule("inventory_alert_summary", ("오늘 확인해야 할 재고", "오늘 확인할 재고", "재고 경고 요약", "재고 이상 품목", "재고 이상"), 250, "alert"),
        IntentRule("inventory_out_of_stock", ("품절 품목", "품절 재고"), 249, "alert"),
        IntentRule("inventory_alert_negative", ("음수 재고 있어", "음수 재고 품목"), 248, "alert"),
        IntentRule("inventory_rapid_decrease", ("급격히 줄어", "급감 품목", "재고 급감"), 247, "alert"),
        IntentRule("inventory_alert_low_stock", ("재고 부족 품목", "부족 재고 경고"), 246, "alert"),
        IntentRule("inventory_largest_decrease", ("가장 많이 감소", "가장 크게 감소", "가장 많이 줄"), 230, "history_change"),
        IntentRule("inventory_largest_increase", ("가장 많이 증가", "가장 크게 증가", "가장 많이 늘"), 229, "history_change"),
        IntentRule("inventory_change_summary", ("재고 변화 요약", "재고 증감 요약"), 228, "history_change"),
        IntentRule("inventory_decreased", ("재고가 줄어든", "재고 감소", "감소한 품목", "보다 줄어든"), 227, "history_change"),
        IntentRule("inventory_increased", ("재고가 늘어난", "재고 증가", "증가한 품목", "보다 늘어난"), 226, "history_change"),
        IntentRule("inventory_history_compare", ("최근 재고 변화", "변화가 큰 품목", "재고 변동"), 225, "history_change"),
        IntentRule("inventory_change_compare", ("오전 오후", "오전과 오후", "오전보다", "어제보다", "재고 변화 비교", "시간 재고 비교"), 224, "history_change"),
        IntentRule("inventory_compare", ("비교", "중 어느 게", "중 어느것"), 170, "compare_items"),
        IntentRule("inventory_sort", ("적은 순", "낮은 순", "많은 순", "높은 순", "수량 적은 순", "수량 많은 순"), 160, "sort"),
        IntentRule("inventory_zero", ("재고 0개", "재고가 0개", "재고 없는", "재고가 없는"), 150),
        IntentRule("inventory_negative", ("음수 재고", "마이너스 재고", "재고가 음수"), 145),
        IntentRule("inventory_max", ("가장 많은 품목", "재고가 가장 많은", "최대 재고"), 140),
        IntentRule("inventory_min", ("가장 적은 품목", "재고가 가장 적은", "최소 재고"), 135),
        # 기존 부족 재고 intent를 유지하면서 이하 조건 분석에도 재사용한다.
        IntentRule("inventory_low_stock", ("재고 부족", "부족 재고", "적게 남은", "이하", "미만"), 131, "threshold"),
        IntentRule("inventory_filter", ("이상 품목", "개 이상"), 130, "condition"),
        IntentRule("inventory_item_code", ("품목코드", "품목 코드"), 132, "item_code"),
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
    is_time_change_question = (
        "재고" in normalized
        and (
            ("오전" in normalized and ("오후" in normalized or "오전보다" in normalized))
            or "어제보다" in normalized
        )
    )
    if is_time_change_question:
        intent = (
            "inventory_decreased" if any(value in normalized for value in ("감소", "줄어", "줄었"))
            else "inventory_increased" if any(value in normalized for value in ("증가", "늘어", "늘었"))
            else "inventory_change_compare"
        )
        return IntentResult(intent, normalized, _parse_entities("history_change", normalized), read_only_violation)
    for rule in INTENT_RULES:
        if any(keyword in normalized for keyword in rule.keywords):
            entities = _parse_entities(rule.parser, normalized)
            return IntentResult(rule.intent, normalized, entities, read_only_violation)
    return IntentResult("unknown", normalized, {}, read_only_violation)


def _parse_entities(parser: Optional[str], message: str) -> Dict[str, Any]:
    if parser == "alert":
        return {}
    if parser == "history_change":
        entities = {
            "mode": (
                "today_vs_yesterday" if "어제" in message
                else "today_morning_afternoon" if "오전" in message and ("오후" in message or "오전보다" in message)
                else "latest_previous"
            ),
            "today_only": "오늘" in message and "어제" not in message,
            "direction": (
                "decreased" if any(value in message for value in ("감소", "줄어", "줄었"))
                else "increased" if any(value in message for value in ("증가", "늘어", "늘었"))
                else "all"
            ),
        }
        code_match = re.search(r"품목\s*코드\s*[:#]?\s*([a-z0-9][a-z0-9._-]*)", message, re.IGNORECASE)
        if code_match:
            entities["item_code"] = code_match.group(1).upper()
        else:
            name_match = re.search(r"품목(?:명)?\s+([^\s]+)", message)
            excluded = {"변화", "재고", "보여줘", "알려줘", "조회", "비교", "비교해줘"}
            if name_match and name_match.group(1) not in excluded:
                entities["keyword"] = name_match.group(1)
            else:
                leading_match = re.match(r"([^\s]+)\s+(?:오전|어제)", message)
                if leading_match and leading_match.group(1) not in {"오늘", "재고", "품목"}:
                    entities["keyword"] = leading_match.group(1)
        return entities
    if parser == "threshold":
        match = re.search(r"(\d+)\s*개?\s*(이하|미만)", message)
        return {
            "threshold": int(match.group(1)) if match else 10,
            "comparison": match.group(2) if match else "이하",
        }
    if parser == "compare_items":
        cleaned = re.sub(r"(?:재고|수량)?\s*(?:비교해줘|비교|중 어느 게 더 많아|중 어느것이 더 많아)", "", message)
        parts = [
            part.strip()
            for part in re.split(
                r"\s*(?:이랑|랑|하고|,|/)\s*|(?<=\S)(?:와|과)\s+(?=\S)",
                cleaned,
            )
            if part.strip()
        ]
        return {"items": parts[:10]}
    if parser == "sort":
        descending = any(phrase in message for phrase in ("많은 순", "높은 순", "수량 많은 순"))
        return {"direction": "desc" if descending else "asc"}
    if parser == "condition":
        match = re.search(r"(\d+(?:\.\d+)?)\s*개?\s*(이하|이상)", message)
        if not match:
            return {}
        return {
            "threshold": match.group(1),
            "comparison": "lte" if match.group(2) == "이하" else "gte",
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
