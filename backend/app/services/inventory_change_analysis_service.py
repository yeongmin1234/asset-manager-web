from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot


KOREA = ZoneInfo("Asia/Seoul")
VALID_DIRECTIONS = {"all", "increased", "decreased", "unchanged"}
VALID_MODES = {"latest_previous", "today_morning_afternoon", "today_vs_yesterday", "custom"}
VALID_EXTREMES = {"largest_increase", "largest_decrease"}
NEAREST_TOLERANCE = timedelta(hours=12)


@dataclass(frozen=True)
class SnapshotGroup:
    group_id: str
    snapshot_at: datetime
    schedule_id: Optional[int]


class InventoryChangeAnalysisService:
    def __init__(self, now_func=None):
        self.now_func = now_func or (lambda: datetime.now(timezone.utc))

    def compare(
        self,
        db: Session,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        item_code: Optional[str] = None,
        keyword: Optional[str] = None,
        schedule_id: Optional[int] = None,
        start_schedule_id: Optional[int] = None,
        end_schedule_id: Optional[int] = None,
        direction: str = "all",
        extreme: Optional[str] = None,
        mode: str = "latest_previous",
        today_only: bool = False,
        limit: int = 200,
    ) -> Dict[str, Any]:
        normalized_direction = (direction or "all").strip().lower()
        normalized_mode = (mode or "latest_previous").strip().lower()
        if normalized_direction not in VALID_DIRECTIONS:
            raise ValueError("direction은 increased, decreased, unchanged, all 중 하나여야 합니다.")
        if normalized_mode not in VALID_MODES:
            raise ValueError("지원하지 않는 재고 변화 비교 방식입니다.")
        if extreme is not None and extreme not in VALID_EXTREMES:
            raise ValueError("지원하지 않는 최대 변화 조건입니다.")
        if limit < 1 or limit > 200:
            raise ValueError("조회 건수는 1건 이상 200건 이하로 입력해주세요.")

        groups = self._load_groups(db, schedule_id)
        before_group, after_group, selection_note = self._select_groups(
            groups, normalized_mode, start_at, end_at, start_schedule_id,
            end_schedule_id, today_only,
        )
        if before_group is None or after_group is None:
            return self._empty_response(selection_note)

        before_rows = self._load_totals(db, before_group.group_id, item_code, keyword)
        after_rows = self._load_totals(db, after_group.group_id, item_code, keyword)
        all_items = self._calculate_changes(before_rows, after_rows)
        summary = self._summarize(all_items)
        if extreme:
            target = summary[extreme]
            filtered = (
                [item for item in all_items if target and item["change_quantity"] == target["change_quantity"]]
                if target else []
            )
        else:
            filtered = self._filter_direction(all_items, normalized_direction)
            filtered = self._sort_items(filtered, normalized_direction)
        filtered = filtered[:limit]
        answer = self._build_answer(
            before_group, after_group, normalized_direction, filtered, summary, extreme,
        )
        label = "{} 대비 {} 재고 변화".format(
            self._format_korea(before_group.snapshot_at), self._format_korea(after_group.snapshot_at),
        )
        return {
            "success": True,
            "available": True,
            "start_at": before_group.snapshot_at.astimezone(KOREA),
            "end_at": after_group.snapshot_at.astimezone(KOREA),
            "start_snapshot_group_id": before_group.group_id,
            "end_snapshot_group_id": after_group.group_id,
            "start_schedule_id": before_group.schedule_id,
            "end_schedule_id": after_group.schedule_id,
            "selection_note": selection_note,
            "total_items": len(all_items),
            "total": len(filtered),
            "increased_count": summary["increased_count"],
            "decreased_count": summary["decreased_count"],
            "unchanged_count": summary["unchanged_count"],
            "largest_increase": summary["largest_increase"],
            "largest_decrease": summary["largest_decrease"],
            "items": filtered,
            "message": "재고 변화 분석에 성공했습니다.",
            "answer": answer,
            "analysis": {
                "type": "inventory_change",
                "label": label,
                "direction": normalized_direction,
                "extreme": extreme,
                "selection_note": selection_note,
                "limited": len(self._filter_direction(all_items, normalized_direction)) > limit,
                "scope_limit": limit,
            },
        }

    def summary(self, db: Session, **kwargs) -> Dict[str, Any]:
        kwargs["direction"] = "all"
        return self.compare(db, **kwargs)

    def _load_groups(self, db: Session, schedule_id: Optional[int]) -> List[SnapshotGroup]:
        query = (
            select(
                InventorySnapshot.snapshot_group_id,
                func.max(InventorySnapshot.snapshot_at),
                func.max(InventorySnapshot.schedule_id),
            )
            .where(InventorySnapshot.row_type == "total")
            .group_by(InventorySnapshot.snapshot_group_id)
            .order_by(func.max(InventorySnapshot.snapshot_at))
        )
        if schedule_id is not None:
            query = query.where(InventorySnapshot.schedule_id == schedule_id)
        return [
            SnapshotGroup(str(group_id), self._aware(snapshot_at), group_schedule_id)
            for group_id, snapshot_at, group_schedule_id in db.execute(query)
        ]

    def _select_groups(
        self, groups, mode, start_at, end_at, start_schedule_id, end_schedule_id, today_only,
    ) -> Tuple[Optional[SnapshotGroup], Optional[SnapshotGroup], str]:
        if len(groups) < 2:
            return None, None, "비교 가능한 스냅샷이 두 개 이상 필요합니다."
        if start_schedule_id is not None or end_schedule_id is not None:
            before = self._latest_for_schedule(groups, start_schedule_id)
            after = self._latest_for_schedule(groups, end_schedule_id)
            if before and after and before.group_id != after.group_id:
                return before, after, "지정된 각 스케줄의 최신 실제 스냅샷을 사용했습니다."
            return None, None, "지정한 두 스케줄에서 비교 가능한 스냅샷을 찾지 못했습니다."

        if start_at is not None or end_at is not None or mode == "custom":
            if start_at is None or end_at is None:
                return None, None, "사용자 지정 비교에는 start_at과 end_at이 모두 필요합니다."
            requested_start = self._normalize_requested(start_at)
            requested_end = self._normalize_requested(end_at)
            if requested_start >= requested_end:
                raise ValueError("start_at은 end_at보다 이전이어야 합니다.")
            before = self._nearest(groups, requested_start)
            after = self._nearest(groups, requested_end)
            if before is None or after is None or before.group_id == after.group_id:
                return None, None, "요청 시각에서 12시간 이내의 서로 다른 스냅샷을 찾지 못했습니다."
            return before, after, "요청 시각에서 12시간 이내 가장 가까운 실제 스냅샷을 사용했습니다."

        now_korea = self._aware(self.now_func()).astimezone(KOREA)
        today = now_korea.date()
        if mode == "today_morning_afternoon":
            today_groups = [group for group in groups if group.snapshot_at.astimezone(KOREA).date() == today]
            if len(today_groups) < 2:
                return None, None, "오늘 비교 가능한 오전·오후 스냅샷을 찾지 못했습니다."
            return today_groups[0], today_groups[-1], "오늘의 최초 및 최신 실제 스냅샷을 사용했습니다."
        if mode == "today_vs_yesterday":
            today_groups = [group for group in groups if group.snapshot_at.astimezone(KOREA).date() == today]
            yesterday = today - timedelta(days=1)
            yesterday_groups = [group for group in groups if group.snapshot_at.astimezone(KOREA).date() == yesterday]
            if not today_groups or not yesterday_groups:
                return None, None, "오늘과 어제의 비교 가능한 스냅샷을 찾지 못했습니다."
            after = today_groups[-1]
            target_time = after.snapshot_at.astimezone(KOREA).timetz().replace(tzinfo=None)
            before = min(
                yesterday_groups,
                key=lambda group: abs(self._seconds_from_time(group.snapshot_at.astimezone(KOREA).time(), target_time)),
            )
            return before, after, "오늘 최신 시각과 어제 동일 시간대에 가장 가까운 실제 스냅샷을 사용했습니다."

        candidates = groups
        if today_only:
            candidates = [group for group in groups if group.snapshot_at.astimezone(KOREA).date() == today]
        if len(candidates) < 2:
            return None, None, "선택한 기간에 비교 가능한 스냅샷을 찾지 못했습니다."
        return candidates[-2], candidates[-1], "가장 최근의 서로 다른 두 스냅샷을 사용했습니다."

    @staticmethod
    def _latest_for_schedule(groups, schedule_id):
        if schedule_id is None:
            return None
        matches = [group for group in groups if group.schedule_id == schedule_id]
        return matches[-1] if matches else None

    @staticmethod
    def _nearest(groups, requested):
        nearest = min(groups, key=lambda group: abs(group.snapshot_at - requested))
        return nearest if abs(nearest.snapshot_at - requested) <= NEAREST_TOLERANCE else None

    def _load_totals(self, db, group_id, item_code, keyword):
        query = select(InventorySnapshot).where(
            InventorySnapshot.snapshot_group_id == group_id,
            InventorySnapshot.row_type == "total",
        )
        if item_code:
            query = query.where(InventorySnapshot.item_code == item_code.strip().upper())
        if keyword:
            pattern = "%{}%".format(keyword.strip())
            query = query.where(or_(
                InventorySnapshot.item_name.ilike(pattern), InventorySnapshot.item_code.ilike(pattern),
            ))
        return {row.item_code: row for row in db.scalars(query)}

    def _calculate_changes(self, before_rows, after_rows):
        items = []
        for code in sorted(set(before_rows) | set(after_rows)):
            before_row = before_rows.get(code)
            after_row = after_rows.get(code)
            before = Decimal(before_row.total_quantity) if before_row else Decimal("0")
            after = Decimal(after_row.total_quantity) if after_row else Decimal("0")
            change = after - before
            status, change_rate, rate_label = self._classify(
                before, after, change, before_row is not None, after_row is not None,
            )
            source = after_row or before_row
            items.append({
                "item_code": code,
                "item_name": source.item_name,
                "unit": source.unit,
                "before_quantity": before,
                "after_quantity": after,
                "change_quantity": change,
                "change_rate": change_rate,
                "change_rate_label": rate_label,
                "status": status,
                "total_quantity": after,
                "warehouses": [],
            })
        return items

    @staticmethod
    def _classify(before, after, change, existed_before, exists_after):
        if existed_before and not exists_after:
            status = "no_longer_present"
        elif not existed_before and exists_after:
            status = "negative_transition" if after < 0 else "newly_added"
        elif before >= 0 and after < 0:
            status = "negative_transition"
        elif change > 0:
            status = "newly_added" if before == 0 else "increased"
        elif change < 0:
            status = "decreased"
        else:
            status = "unchanged"
        if before == 0:
            if after > 0:
                return status, None, "신규 증가"
            if after < 0:
                return status, None, "음수 전환"
            return status, None, "변화 없음"
        rate = ((change / abs(before)) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP,
        )
        return status, rate, None

    @staticmethod
    def _filter_direction(items, direction):
        if direction == "increased":
            return [item for item in items if item["change_quantity"] > 0]
        if direction == "decreased":
            return [item for item in items if item["change_quantity"] < 0]
        if direction == "unchanged":
            return [item for item in items if item["change_quantity"] == 0]
        return list(items)

    @staticmethod
    def _sort_items(items, direction):
        if direction == "increased":
            return sorted(items, key=lambda item: item["change_quantity"], reverse=True)
        if direction == "decreased":
            return sorted(items, key=lambda item: item["change_quantity"])
        if direction == "unchanged":
            return sorted(items, key=lambda item: item["item_code"])
        return sorted(items, key=lambda item: abs(item["change_quantity"]), reverse=True)

    @staticmethod
    def _summarize(items):
        increased = [item for item in items if item["change_quantity"] > 0]
        decreased = [item for item in items if item["change_quantity"] < 0]
        unchanged = [item for item in items if item["change_quantity"] == 0]
        return {
            "increased_count": len(increased),
            "decreased_count": len(decreased),
            "unchanged_count": len(unchanged),
            "largest_increase": max(increased, key=lambda item: item["change_quantity"]) if increased else None,
            "largest_decrease": min(decreased, key=lambda item: item["change_quantity"]) if decreased else None,
        }

    def _build_answer(self, before, after, direction, items, summary, extreme=None):
        period = "{} 대비 {} 기준".format(
            self._format_korea(before.snapshot_at), self._format_korea(after.snapshot_at),
        )
        if extreme == "largest_decrease":
            largest = summary["largest_decrease"]
            message = (
                "{}\n가장 많이 감소한 품목은 {}이며 {}개 감소했습니다.".format(
                    period, largest["item_name"] or largest["item_code"], self._format_decimal(abs(largest["change_quantity"])),
                ) if largest else "{}\n감소한 품목이 없습니다.".format(period)
            )
        elif extreme == "largest_increase":
            largest = summary["largest_increase"]
            message = (
                "{}\n가장 많이 증가한 품목은 {}이며 {}개 증가했습니다.".format(
                    period, largest["item_name"] or largest["item_code"], self._format_decimal(largest["change_quantity"]),
                ) if largest else "{}\n증가한 품목이 없습니다.".format(period)
            )
        elif direction == "decreased":
            message = "{}\n재고가 감소한 품목은 {}개입니다.".format(period, len(items))
            largest = summary["largest_decrease"]
            if largest:
                message += "\n가장 많이 감소한 품목은 {}이며 {}개 감소했습니다.".format(
                    largest["item_name"] or largest["item_code"], self._format_decimal(abs(largest["change_quantity"])),
                )
        elif direction == "increased":
            message = "{}\n재고가 증가한 품목은 {}개입니다.".format(period, len(items))
            largest = summary["largest_increase"]
            if largest:
                message += "\n가장 많이 증가한 품목은 {}이며 {}개 증가했습니다.".format(
                    largest["item_name"] or largest["item_code"], self._format_decimal(largest["change_quantity"]),
                )
        elif len(items) == 1:
            item = items[0]
            message = "{}의 재고는\n{} {}개,\n{} {}개입니다.\n증감은 {}개입니다.".format(
                item["item_name"] or item["item_code"], self._format_korea(before.snapshot_at),
                self._format_decimal(item["before_quantity"]), self._format_korea(after.snapshot_at),
                self._format_decimal(item["after_quantity"]), self._format_decimal(item["change_quantity"]),
            )
        else:
            message = (
                "{}\n총 {}개 품목을 비교했습니다.\n증가 {}개, 감소 {}개, 변화 없음 {}개입니다."
            ).format(
                period, summary["increased_count"] + summary["decreased_count"] + summary["unchanged_count"],
                summary["increased_count"], summary["decreased_count"], summary["unchanged_count"],
            )
        return message + "\n상세 결과는 왼쪽 재고 조회 결과에서 확인할 수 있습니다."

    @staticmethod
    def _empty_response(note):
        return {
            "success": True, "available": False, "start_at": None, "end_at": None,
            "start_snapshot_group_id": None, "end_snapshot_group_id": None,
            "start_schedule_id": None, "end_schedule_id": None,
            "selection_note": note, "total_items": 0, "total": 0,
            "increased_count": 0, "decreased_count": 0, "unchanged_count": 0,
            "largest_increase": None, "largest_decrease": None, "items": [],
            "message": "비교할 재고 이력이 없습니다.",
            "answer": "비교할 재고 이력이 없습니다.\n정기 재고 조회가 실행된 후 다시 확인해 주세요.",
            "analysis": {"type": "inventory_change", "label": "재고 변화", "selection_note": note},
        }

    @staticmethod
    def _format_korea(value):
        return value.astimezone(KOREA).strftime("%m월 %d일 %H시 %M분")

    @staticmethod
    def _format_decimal(value):
        raw = format(Decimal(value), "f")
        return raw.rstrip("0").rstrip(".") if "." in raw else raw

    @staticmethod
    def _aware(value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_requested(value):
        if value.tzinfo is None:
            return value.replace(tzinfo=KOREA).astimezone(timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _seconds_from_time(left, right):
        return (left.hour * 3600 + left.minute * 60 + left.second) - (
            right.hour * 3600 + right.minute * 60 + right.second
        )
