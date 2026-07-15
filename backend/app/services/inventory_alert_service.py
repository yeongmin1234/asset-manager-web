from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.inventory_alert import InventoryAlert
from app.models.inventory_alert_rule import InventoryAlertRule
from app.models.inventory_snapshot import InventorySnapshot


OPEN_STATUSES = ("active", "acknowledged")


class InventoryAlertService:
    """Evaluates persisted snapshots only; it never mutates ECOUNT inventory."""

    @staticmethod
    def _rate(before: Decimal, change: Decimal) -> Optional[Decimal]:
        if before == 0:
            return None
        return (change / abs(before)) * Decimal("100")

    @classmethod
    def detect_for_snapshot_group(
        cls, db: Session, snapshot_group_id: str, partial_result: bool = False
    ) -> Dict[str, int]:
        current = db.query(InventorySnapshot).filter(
            InventorySnapshot.snapshot_group_id == snapshot_group_id,
            InventorySnapshot.warehouse_code.is_(None),
        ).all()
        if not current:
            raise ValueError("감지할 재고 스냅샷이 없습니다.")

        current_at = current[0].snapshot_at
        previous_group = (
            db.query(InventorySnapshot.snapshot_group_id)
            .filter(
                InventorySnapshot.warehouse_code.is_(None),
                InventorySnapshot.snapshot_at < current_at,
                InventorySnapshot.snapshot_group_id != snapshot_group_id,
            )
            .order_by(InventorySnapshot.snapshot_at.desc())
            .first()
        )
        previous = {}
        if previous_group:
            previous = {
                row.item_code: row
                for row in db.query(InventorySnapshot).filter(
                    InventorySnapshot.snapshot_group_id == previous_group[0],
                    InventorySnapshot.warehouse_code.is_(None),
                ).all()
            }

        rules = db.query(InventoryAlertRule).filter(InventoryAlertRule.is_active.is_(True)).all()
        triggered = set()
        created = updated = 0
        now = datetime.now(timezone.utc)

        for row in current:
            quantity = Decimal(row.total_quantity)
            prior = previous.get(row.item_code)
            before = Decimal(prior.total_quantity) if prior else None
            change = quantity - before if before is not None else None
            rate = cls._rate(before, change) if before is not None else None
            for rule in rules:
                if rule.item_code and rule.item_code != row.item_code:
                    continue
                matched = False
                if rule.alert_type == "OUT_OF_STOCK":
                    matched = quantity == 0
                elif rule.alert_type == "LOW_STOCK" and rule.threshold_quantity is not None:
                    matched = quantity <= Decimal(rule.threshold_quantity)
                elif rule.alert_type == "NEGATIVE_STOCK":
                    matched = quantity < 0
                elif rule.alert_type == "RAPID_DECREASE" and change is not None and change < 0:
                    within_window = True
                    if rule.comparison_minutes and prior:
                        within_window = (current_at - prior.snapshot_at).total_seconds() <= rule.comparison_minutes * 60
                    qty_hit = rule.threshold_change_quantity is not None and abs(change) >= Decimal(rule.threshold_change_quantity)
                    rate_hit = rule.threshold_change_rate is not None and rate is not None and abs(rate) >= Decimal(rule.threshold_change_rate)
                    matched = within_window and (qty_hit or rate_hit)
                if not matched:
                    continue

                key = (rule.id, row.item_code, rule.alert_type)
                triggered.add(key)
                alert = db.query(InventoryAlert).filter(
                    InventoryAlert.rule_id == rule.id,
                    InventoryAlert.item_code == row.item_code,
                    InventoryAlert.alert_type == rule.alert_type,
                    InventoryAlert.status.in_(OPEN_STATUSES),
                ).first()
                threshold = cls._threshold_text(rule)
                if alert is None:
                    alert = InventoryAlert(
                        rule_id=rule.id, alert_type=rule.alert_type, severity=rule.severity,
                        item_code=row.item_code, item_name=row.item_name,
                        detected_at=now, status="active", created_at=now,
                    )
                    db.add(alert)
                    created += 1
                else:
                    updated += 1
                alert.last_detected_at = now
                alert.snapshot_id = row.id
                alert.previous_quantity = before
                alert.current_quantity = quantity
                alert.change_quantity = change
                alert.change_rate = rate
                alert.threshold_description = threshold
                alert.partial_result = partial_result
                alert.safe_message = "%s: %s 재고 확인이 필요합니다." % (row.item_name, rule.name)
                alert.updated_at = now

        resolved = 0
        current_codes = {row.item_code for row in current}
        open_alerts = db.query(InventoryAlert).filter(InventoryAlert.status.in_(OPEN_STATUSES)).all()
        active_rule_ids = {rule.id for rule in rules}
        for alert in open_alerts:
            key = (alert.rule_id, alert.item_code, alert.alert_type)
            if alert.rule_id in active_rule_ids and alert.item_code in current_codes and key not in triggered:
                alert.status = "resolved"
                alert.resolved_at = now
                alert.updated_at = now
                resolved += 1
        db.flush()
        return {"created": created, "updated": updated, "resolved": resolved, "evaluated": len(current)}

    @staticmethod
    def _threshold_text(rule: InventoryAlertRule) -> str:
        if rule.alert_type == "OUT_OF_STOCK":
            return "재고 0"
        if rule.alert_type == "NEGATIVE_STOCK":
            return "재고 0 미만"
        if rule.alert_type == "LOW_STOCK":
            return "재고 %s 이하" % rule.threshold_quantity
        parts = []
        if rule.threshold_change_quantity is not None:
            parts.append("감소량 %s 이상" % rule.threshold_change_quantity)
        if rule.threshold_change_rate is not None:
            parts.append("감소율 %s%% 이상" % rule.threshold_change_rate)
        return " 또는 ".join(parts)
