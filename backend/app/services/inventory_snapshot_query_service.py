from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import List, Optional
try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.8
    from backports.zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.inventory_snapshot import InventorySnapshot


def get_latest_snapshot(
    db: Session,
    item_code: Optional[str] = None,
    keyword: Optional[str] = None,
    schedule_id: Optional[int] = None,
):
    group_query = select(InventorySnapshot.snapshot_group_id).where(InventorySnapshot.row_type == "total")
    if schedule_id is not None:
        group_query = group_query.where(InventorySnapshot.schedule_id == schedule_id)
    group_query = group_query.order_by(InventorySnapshot.snapshot_at.desc()).limit(1)
    group_id = db.scalar(group_query)
    if not group_id:
        return {"snapshot_group_id": None, "schedule_id": schedule_id, "snapshot_at": None, "total": 0, "items": []}

    query = select(InventorySnapshot).where(InventorySnapshot.snapshot_group_id == group_id)
    if item_code:
        query = query.where(InventorySnapshot.item_code == item_code.strip().upper())
    if keyword:
        normalized = "%{}%".format(keyword.strip())
        query = query.where(or_(
            InventorySnapshot.item_name.ilike(normalized),
            InventorySnapshot.item_code.ilike(normalized),
        ))
    rows = list(db.scalars(query.order_by(InventorySnapshot.item_code, InventorySnapshot.row_type.desc())))
    return _group_snapshot_rows(rows)


def get_snapshot_history(
    db: Session,
    item_code: Optional[str] = None,
    keyword: Optional[str] = None,
    snapshot_date: Optional[date] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    schedule_id: Optional[int] = None,
    limit: int = 200,
):
    query = select(InventorySnapshot).where(InventorySnapshot.row_type == "total")
    if item_code:
        query = query.where(InventorySnapshot.item_code == item_code.strip().upper())
    if keyword:
        pattern = "%{}%".format(keyword.strip())
        query = query.where(or_(InventorySnapshot.item_name.ilike(pattern), InventorySnapshot.item_code.ilike(pattern)))
    if schedule_id is not None:
        query = query.where(InventorySnapshot.schedule_id == schedule_id)
    if snapshot_date:
        korea = ZoneInfo("Asia/Seoul")
        day_start = datetime.combine(snapshot_date, time.min).replace(tzinfo=korea).astimezone(timezone.utc)
        day_end = datetime.combine(snapshot_date, time.max).replace(tzinfo=korea).astimezone(timezone.utc)
        query = query.where(InventorySnapshot.snapshot_at.between(day_start, day_end))
    if start_at:
        query = query.where(InventorySnapshot.snapshot_at >= start_at)
    if end_at:
        query = query.where(InventorySnapshot.snapshot_at <= end_at)
    return list(db.scalars(query.order_by(InventorySnapshot.snapshot_at.desc(), InventorySnapshot.item_code).limit(limit)))


def compare_latest_snapshots(
    db: Session, item_code: Optional[str] = None, keyword: Optional[str] = None,
    schedule_id: Optional[int] = None,
):
    group_query = (
        select(InventorySnapshot.snapshot_group_id, func.max(InventorySnapshot.snapshot_at).label("snapshot_at"))
        .where(InventorySnapshot.row_type == "total")
        .group_by(InventorySnapshot.snapshot_group_id)
        .order_by(func.max(InventorySnapshot.snapshot_at).desc())
        .limit(2)
    )
    if schedule_id is not None:
        group_query = group_query.where(InventorySnapshot.schedule_id == schedule_id)
    groups = list(db.execute(group_query))
    if len(groups) < 2:
        return {"previous_snapshot_at": None, "current_snapshot_at": groups[0][1] if groups else None, "total": 0, "items": []}
    current_group, current_at = groups[0]
    previous_group, previous_at = groups[1]
    rows_query = select(InventorySnapshot).where(and_(
        InventorySnapshot.row_type == "total",
        InventorySnapshot.snapshot_group_id.in_([current_group, previous_group]),
    ))
    if item_code:
        rows_query = rows_query.where(InventorySnapshot.item_code == item_code.strip().upper())
    if keyword:
        pattern = "%{}%".format(keyword.strip())
        rows_query = rows_query.where(or_(InventorySnapshot.item_name.ilike(pattern), InventorySnapshot.item_code.ilike(pattern)))
    rows = list(db.scalars(rows_query))
    previous = {row.item_code: row for row in rows if row.snapshot_group_id == previous_group}
    current = {row.item_code: row for row in rows if row.snapshot_group_id == current_group}
    items = []
    for code in sorted(set(previous) | set(current)):
        old = previous.get(code)
        new = current.get(code)
        old_quantity = Decimal(old.total_quantity) if old else Decimal("0")
        new_quantity = Decimal(new.total_quantity) if new else Decimal("0")
        source = new or old
        items.append({
            "item_code": code,
            "item_name": source.item_name,
            "previous_quantity": old_quantity,
            "current_quantity": new_quantity,
            "difference": new_quantity - old_quantity,
        })
    return {
        "previous_snapshot_at": previous_at, "current_snapshot_at": current_at,
        "total": len(items), "items": items,
    }


def _group_snapshot_rows(rows: List[InventorySnapshot]):
    if not rows:
        return {"snapshot_group_id": None, "schedule_id": None, "snapshot_at": None, "total": 0, "items": []}
    grouped = {}
    for row in rows:
        item = grouped.setdefault(row.item_code, {
            "item_code": row.item_code, "item_name": row.item_name, "unit": row.unit,
            "total_quantity": row.total_quantity, "warehouses": [],
        })
        if row.row_type == "total":
            item["total_quantity"] = row.total_quantity
        else:
            item["warehouses"].append({
                "warehouse_code": "" if row.warehouse_code.startswith("__UNKNOWN_") else row.warehouse_code,
                "warehouse_name": row.warehouse_name, "quantity": row.quantity,
            })
    first = rows[0]
    return {
        "snapshot_group_id": first.snapshot_group_id, "schedule_id": first.schedule_id,
        "snapshot_at": first.snapshot_at, "total": len(grouped), "items": list(grouped.values()),
    }
