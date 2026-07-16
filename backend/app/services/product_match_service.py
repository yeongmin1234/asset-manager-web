import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


FUZZY_MATCH_THRESHOLD = 0.72
THREE_CHAR_THRESHOLD = 0.82
SHORT_QUERY_THRESHOLD = 0.90
MAX_FUZZY_CANDIDATES = 8

PRODUCT_ALIASES = {
    "렌턴": "랜턴",
    "토스타": "토스터",
}


def normalize_product_text(value: Any, compact: bool = False, apply_aliases: bool = False) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[_,]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    if apply_aliases:
        for alias, canonical in PRODUCT_ALIASES.items():
            text = text.replace(alias, canonical)
    return text.replace(" ", "") if compact else text


def prepare_product_search_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    auxiliary = " ".join(str(item.get(field) or "") for field in (
        "size", "search_text", "barcode", "group_name_1", "group_name_2", "group_name_3",
    ))
    return {
        "code": str(item.get("item_code") or "").strip().casefold(),
        "name": normalize_product_text(item.get("item_name")),
        "name_compact": normalize_product_text(item.get("item_name"), compact=True),
        "auxiliary": normalize_product_text(auxiliary, compact=True),
    }


def fuzzy_threshold(query: str) -> float:
    length = len(normalize_product_text(query, compact=True))
    if length <= 2:
        return SHORT_QUERY_THRESHOLD
    if length == 3:
        return THREE_CHAR_THRESHOLD
    return FUZZY_MATCH_THRESHOLD


def rank_product_matches(products: List[Dict[str, Any]], query: str, limit: int = 8) -> Dict[str, Any]:
    display_query = re.sub(r"\s+", " ", str(query or "").strip())
    normalized = normalize_product_text(display_query)
    compact = normalize_product_text(display_query, compact=True)
    code_query = display_query.casefold()
    if not compact:
        return {"match_type": "none", "items": [], "total": 0, "highest_score": None}

    buckets = []
    for item in products:
        fields = item.get("_search") or prepare_product_search_fields(item)
        if fields["code"] == code_query:
            buckets.append((0, 1.0, "exact_code", "품목코드 정확 일치", item))
        elif fields["name"] == normalized:
            buckets.append((1, 1.0, "exact_name", "품목명 정확 일치", item))
        elif fields["name_compact"] == compact:
            buckets.append((2, 1.0, "space_normalized", "공백 차이 일치", item))
        elif fields["name_compact"].startswith(compact):
            buckets.append((3, 1.0, "prefix", "품목명 시작 일치", item))
        elif compact in fields["name_compact"]:
            buckets.append((4, 1.0, "partial", "품목명 부분 일치", item))

    if buckets and min(row[0] for row in buckets) <= 2:
        best_rank = min(row[0] for row in buckets)
        buckets = [row for row in buckets if row[0] == best_rank]

    # Exact/name matches are authoritative. Code prefixes are only offered when
    # no name match exists and are never typo-corrected or auto-selected.
    if not buckets and re.fullmatch(r"[a-z0-9][a-z0-9./-]*", code_query, re.IGNORECASE):
        for item in products:
            fields = item.get("_search") or prepare_product_search_fields(item)
            if fields["code"].startswith(code_query):
                buckets.append((5, 1.0, "code_prefix", "품목코드 시작 일치", item))

    if not buckets:
        alias_query = normalize_product_text(display_query, compact=True, apply_aliases=True)
        threshold = fuzzy_threshold(alias_query)
        for item in products:
            fields = item.get("_search") or prepare_product_search_fields(item)
            name = normalize_product_text(fields["name_compact"], compact=True, apply_aliases=True)
            name_score = SequenceMatcher(None, alias_query, name).ratio()
            compact_score = SequenceMatcher(None, compact, fields["name_compact"]).ratio()
            aux_score = SequenceMatcher(None, alias_query, fields["auxiliary"]).ratio() if fields["auxiliary"] else 0.0
            weighted = (name_score * 0.7) + (compact_score * 0.2)
            score = weighted / 0.9
            if fields["auxiliary"]:
                score = max(score, (score * 0.9) + (aux_score * 0.1))
            score = round(score, 4)
            if score >= threshold:
                buckets.append((6, score, "fuzzy", "품목명 유사", item))

    buckets.sort(key=lambda row: (
        row[0], -row[1], len(str(row[4].get("item_name") or "")), str(row[4].get("item_code") or ""),
    ))
    selected = buckets[:min(MAX_FUZZY_CANDIDATES, max(1, limit))]
    items = []
    for _, score, match_type, reason, item in selected:
        items.append({
            "item_code": item["item_code"], "item_name": item.get("item_name"),
            "size": item.get("size"), "unit": item.get("unit"),
            "match_score": score, "match_reason": reason, "match_type": match_type,
        })
    overall_type = selected[0][2] if selected else "none"
    return {
        "match_type": overall_type, "items": items, "total": len(buckets),
        "highest_score": selected[0][1] if selected else None,
    }
