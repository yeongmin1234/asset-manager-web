import time
from datetime import timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8
    from backports.zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.services.ai_inventory_context_service import get_inventory_context
from app.services.inventory_service import InventoryService, MAX_RESULT_LIMIT
from app.services.inventory_snapshot_query_service import get_latest_snapshot


ANALYSIS_INTENTS = {
    "inventory_compare",
    "inventory_sort",
    "inventory_filter",
    "inventory_low_stock",
    "inventory_min",
    "inventory_max",
    "inventory_zero",
    "inventory_negative",
}


class InventorySnapshotUnavailableError(ValueError):
    pass


class InventoryAnalysisService:
    def __init__(
        self,
        inventory_service: Optional[InventoryService] = None,
        db: Optional[Session] = None,
    ):
        self.inventory_service = inventory_service or InventoryService()
        self.db = db

    def analyze(
        self,
        intent: str,
        user_id: int,
        queries: Optional[List[str]] = None,
        direction: Optional[str] = None,
        comparison: Optional[str] = None,
        threshold: Optional[str] = None,
    ) -> Dict[str, Any]:
        if intent not in ANALYSIS_INTENTS:
            raise ValueError("지원하지 않는 재고 분석 요청입니다.")
        started_at = time.monotonic()
        if intent == "inventory_compare":
            items = self._load_comparison_items(user_id, queries or [])
            result_items, answer, label = self._compare(items)
            limited = False
            source = {
                "data_source": "realtime",
                "data_source_label": "실시간 재고",
                "snapshot_at": None,
            }
        else:
            items, source = self._load_analysis_scope()
            result_items, answer, label = self._analyze_scope(
                intent, items, direction, comparison, threshold,
            )
            limited = source["data_source"] == "realtime"
            if source["data_source"] == "snapshot":
                answer = "{}\n기준 시각: {}\n데이터: 최근 동기화 재고".format(
                    answer,
                    self._format_snapshot_at(source["snapshot_at"]),
                )
            else:
                answer = "{}\n현재 조회 가능한 최대 200개 재고 항목을 기준으로 분석했습니다.".format(answer)

        return {
            "success": True,
            "authenticated": True,
            "total": len(result_items),
            "items": result_items,
            "message": "재고 분석에 성공했습니다." if result_items else "분석 조건에 맞는 재고가 없습니다.",
            "response_time_ms": max(0, int((time.monotonic() - started_at) * 1000)),
            "answer": answer,
            "analysis": {
                "type": intent,
                "label": label,
                "limited": limited,
                "scope_limit": MAX_RESULT_LIMIT if limited else None,
                **source,
            },
        }

    def _load_comparison_items(self, user_id: int, queries: List[str]) -> List[Dict[str, Any]]:
        cleaned = [query.strip() for query in queries if query and query.strip()]
        if len(cleaned) < 2:
            context = get_inventory_context(user_id)
            if context and len(context.last_inventory_items) >= 2:
                return context.last_inventory_items
            raise ValueError("비교할 품목을 두 개 이상 입력해주세요.")

        product_matches = self.inventory_service.search_products_for_keywords(cleaned, limit_per_keyword=1)
        items = []
        seen_codes = set()
        for query in cleaned:
            matches = product_matches.get(query) or []
            if not matches:
                continue
            product = matches[0]
            if product["item_code"] in seen_codes:
                continue
            seen_codes.add(product["item_code"])
            locations = self.inventory_service.get_inventory_by_location(
                item_code=product["item_code"], limit=MAX_RESULT_LIMIT,
            )
            items.append(self.inventory_service._aggregate_inventory(product, locations))
        if len(items) < 2:
            raise ValueError("비교 조건에 맞는 품목을 두 개 이상 찾지 못했습니다.")
        return items

    def _load_analysis_scope(self):
        if self.db is not None:
            snapshot = get_latest_snapshot(self.db)
            if not snapshot.get("snapshot_group_id") or not snapshot.get("snapshot_at"):
                raise InventorySnapshotUnavailableError(
                    "최근 재고 스냅샷이 없습니다. 관리자 재고 동기화 또는 예약 작업이 완료된 후 다시 조회해 주세요."
                )
            return snapshot.get("items") or [], {
                "data_source": "snapshot",
                "data_source_label": "최근 동기화 재고",
                "snapshot_at": snapshot.get("snapshot_at"),
                "snapshot_group_id": snapshot.get("snapshot_group_id"),
            }

        products = self.inventory_service.search_products(limit=MAX_RESULT_LIMIT)
        locations = self.inventory_service.get_inventory_by_location(limit=MAX_RESULT_LIMIT)
        products_by_code = {item["item_code"]: item for item in products}
        grouped = {}
        for location in locations:
            grouped.setdefault(location["item_code"], []).append(location)
        items = [
            self.inventory_service._aggregate_inventory(product, grouped.get(code, []))
            for code, product in products_by_code.items()
        ]
        for code, item_locations in grouped.items():
            if code in products_by_code or len(items) >= MAX_RESULT_LIMIT:
                continue
            first = item_locations[0]
            product = {
                "item_code": code,
                "item_name": first.get("item_name"),
                "size": first.get("product_size_description"),
                "unit": None,
            }
            items.append(self.inventory_service._aggregate_inventory(product, item_locations))
        return items[:MAX_RESULT_LIMIT], {
            "data_source": "realtime",
            "data_source_label": "실시간 재고",
            "snapshot_at": None,
        }

    def _compare(self, items: List[Dict[str, Any]]):
        quantities = [self._quantity(item) for item in items]
        minimum = min(quantities)
        maximum = max(quantities)
        result = []
        for item, quantity in zip(items, quantities):
            enriched = dict(item)
            enriched["difference"] = quantity - minimum
            result.append(enriched)
        lines = [
            "{}은(는) {}개".format(item.get("item_name") or item["item_code"], self._format(quantity))
            for item, quantity in zip(items, quantities)
        ]
        item_count = len(items)
        if maximum == minimum:
            subject = "두 품목" if item_count == 2 else "비교한 {}개 품목".format(item_count)
            answer = "{}의 현재 재고는 각각 {}개로 동일합니다.".format(subject, self._format(maximum))
        else:
            winners = [item for item, quantity in zip(items, quantities) if quantity == maximum]
            subject = "두 품목" if item_count == 2 else "{}개 품목".format(item_count)
            if item_count == 2:
                winner_name = winners[0].get("item_name") or winners[0]["item_code"]
                loser = items[quantities.index(minimum)]
                comparison_text = "{} 재고가 {}보다 {}개 더 많습니다.".format(
                    winner_name,
                    loser.get("item_name") or loser["item_code"],
                    self._format(maximum - minimum),
                )
            else:
                comparison_text = "{} 재고가 최저 품목보다 {}개 더 많습니다.".format(
                    ", ".join(item.get("item_name") or item["item_code"] for item in winners),
                    self._format(maximum - minimum),
                )
            answer = "{}을 비교했습니다.\n{}입니다.\n{}".format(
                subject,
                ", ".join(lines),
                comparison_text,
            )
        return result, answer, "품목별 재고 비교"

    def _analyze_scope(self, intent, items, direction, comparison, threshold):
        if not items:
            return [], "현재 조회 범위에 분석할 재고가 없습니다.", "재고 분석"
        if intent == "inventory_sort":
            reverse = direction == "desc"
            sorted_items = sorted(items, key=self._quantity, reverse=reverse)
            result = self._with_ranks(sorted_items)
            label = "재고 많은 순" if reverse else "재고 적은 순"
            return result, "{}으로 {}개 품목을 정렬했습니다.".format(label, len(result)), label
        if intent == "inventory_zero":
            result = [item for item in items if self._quantity(item) == 0]
            return result, "현재 조회 범위에서 재고가 0개인 품목은 {}개입니다.\n상세 결과는 왼쪽 재고 조회 결과에서 확인할 수 있습니다.".format(len(result)), "총재고 = 0"
        if intent == "inventory_negative":
            result = [item for item in items if self._quantity(item) < 0]
            return result, "음수 재고 품목은 {}개입니다.\n재고 정합성 확인이 필요할 수 있습니다.".format(len(result)), "총재고 < 0"
        if intent in {"inventory_filter", "inventory_low_stock"}:
            value = self._decimal(10 if threshold is None else threshold)
            if comparison in {"gte", "이상"}:
                result = [item for item in items if self._quantity(item) >= value]
                label = "총재고 ≥ {}".format(self._format(value))
            elif comparison in {"lt", "미만"}:
                result = [item for item in items if self._quantity(item) < value]
                label = "총재고 < {}".format(self._format(value))
            else:
                result = [item for item in items if self._quantity(item) <= value]
                label = "총재고 ≤ {}".format(self._format(value))
            return result, "{} 조건에 맞는 품목은 {}개입니다.".format(label, len(result)), label
        find_max = intent == "inventory_max"
        target = (max if find_max else min)(self._quantity(item) for item in items)
        result = [item for item in items if self._quantity(item) == target]
        label = "최대 재고" if find_max else "최소 재고"
        return result, "{} 품목은 {}이며, 총재고는 {}개입니다.".format(
            label,
            ", ".join(item.get("item_name") or item["item_code"] for item in result),
            self._format(target),
        ), label

    def _with_ranks(self, items):
        result = []
        previous = None
        rank = 0
        for index, item in enumerate(items, 1):
            quantity = self._quantity(item)
            if quantity != previous:
                rank = index
                previous = quantity
            enriched = dict(item)
            enriched["rank"] = rank
            result.append(enriched)
        return result

    @staticmethod
    def _quantity(item):
        return InventoryAnalysisService._decimal(item.get("total_quantity"))

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("재고 수량을 Decimal로 분석할 수 없습니다.") from exc

    @staticmethod
    def _format(value):
        raw = str(value)
        return raw.rstrip("0").rstrip(".") if "." in raw else raw

    @staticmethod
    def _format_snapshot_at(value):
        if value is None:
            return "확인 불가"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
