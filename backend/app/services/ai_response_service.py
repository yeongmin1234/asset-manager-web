from typing import Any, Dict, Iterable


class AiResponseService:
    """Deterministic formatter: only values present in Backend results are rendered."""

    @staticmethod
    def alert_summary(result: Dict[str, Any]) -> str:
        values = {
            "품절": int(result.get("out_of_stock") or 0),
            "부족 재고": int(result.get("low_stock") or 0),
            "음수 재고": int(result.get("negative_stock") or 0),
            "급감 품목": int(result.get("rapid_decrease") or 0),
        }
        total = int(result.get("active_total") or sum(values.values()))
        lines = ["현재 확인이 필요한 재고 경고는 {}건입니다.".format(total)]
        lines.extend("{} {}건".format(label, count) for label, count in values.items())
        return "\n\n".join((lines[0], "\n".join(lines[1:])))

    @staticmethod
    def limited_items(items: Iterable[Dict[str, Any]], limit: int = 10):
        return list(items)[:max(0, min(int(limit), 10))]
