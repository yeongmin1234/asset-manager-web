import re
from typing import Any, Dict, Optional


WAREHOUSE_STANDALONE_HINTS = {
    "본사", "파주", "rma", "as", "마케팅팀", "물류", "생산",
}
WAREHOUSE_SUFFIXES = ("창고", "센터", "지점")
COMMAND_PATTERN = re.compile(
    r"(?:재고(?:량)?|현재고|보유\s*수량|몇\s*개|알려줘|보여줘|조회해줘|조회|확인해줘|확인|있어|해줘|만)$"
)


def extract_compound_inventory_entities(message: str) -> Optional[Dict[str, Any]]:
    normalized = re.sub(r"\s+", " ", str(message or "").strip().lower())
    if not normalized or not any(token in normalized for token in ("재고", "몇 개", "보여줘", "알려줘")):
        return None

    code_match = re.search(r"품목\s*코드\s*[:#]?\s*([a-z0-9][a-z0-9._/-]*)", normalized, re.IGNORECASE)
    item_code = code_match.group(1).upper() if code_match else None
    working = normalized
    if code_match:
        working = working[:code_match.start()] + " " + working[code_match.end():]
    working = re.sub(r"\b품목\s*코드\b", " ", working)
    working = re.sub(r"(?:재고(?:량)?|현재고|보유\s*수량|몇\s*개|알려줘|보여줘|조회해줘|조회|확인해줘|확인|있어|해줘)", " ", working)
    working = re.sub(r"\s+", " ", working).strip()

    tokens = working.split()
    warehouse_index = None
    warehouse_raw = None
    for index, token in enumerate(tokens):
        cleaned = re.sub(r"(?:에서|에는|에|의|만)$", "", token).strip()
        folded = cleaned.casefold()
        if _looks_like_warehouse(folded):
            warehouse_index = index
            warehouse_raw = cleaned
            break
    if warehouse_index is None or not warehouse_raw:
        return None

    remaining = [token for index, token in enumerate(tokens) if index != warehouse_index]
    keyword = " ".join(remaining).strip()
    keyword = re.sub(r"(?:의|에|에서)$", "", keyword).strip()
    if not item_code and not keyword:
        return None
    return {
        "item_code": item_code,
        "keyword": keyword or None,
        "warehouse_keyword": normalize_warehouse_keyword(warehouse_raw),
        "warehouse_expression": warehouse_raw[:160],
    }


def normalize_warehouse_keyword(value: Any) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
    normalized = re.sub(r"(?:에서|에는|에|의|만)$", "", normalized).strip()
    for suffix in WAREHOUSE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[:-len(suffix)].strip()
            break
    return normalized


def match_warehouses(warehouses, keyword):
    normalized_keyword = normalize_warehouse_keyword(keyword)
    prepared = []
    for row in warehouses or []:
        name = str(row.get("warehouse_name") or "").strip()
        normalized_name = normalize_warehouse_keyword(name)
        prepared.append((name, normalized_name, row))
    raw_keyword = re.sub(r"\s+", " ", str(keyword or "").strip()).casefold()
    exact = [row for name, _, row in prepared if re.sub(r"\s+", " ", name).casefold() == raw_keyword]
    if exact:
        return exact, "exact"
    partial = [row for _, normalized_name, row in prepared if normalized_keyword and normalized_keyword in normalized_name]
    return partial, "partial" if partial else "none"


def _looks_like_warehouse(token: str) -> bool:
    if token in WAREHOUSE_STANDALONE_HINTS:
        return True
    if any(token.endswith(suffix) for suffix in WAREHOUSE_SUFFIXES):
        return True
    return token.endswith("rma") or (len(token) > 2 and token.endswith("as"))
