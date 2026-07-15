from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.inventory_alert import InventoryAlert
from app.models.inventory_alert_rule import InventoryAlertRule
from app.models.inventory_snapshot import InventorySnapshot
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.services.inventory_alert_service import InventoryAlertService

router = APIRouter(prefix="/admin/inventory", tags=["admin-inventory-alerts"])


class RulePayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    alert_type: str
    item_code: Optional[str] = None
    threshold_quantity: Optional[Decimal] = None
    threshold_change_quantity: Optional[Decimal] = None
    threshold_change_rate: Optional[Decimal] = None
    comparison_minutes: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True
    severity: str = "warning"


class ActivePayload(BaseModel):
    is_active: bool


def _rule_dict(row):
    return {key: getattr(row, key) for key in (
        "id", "name", "alert_type", "item_code", "threshold_quantity",
        "threshold_change_quantity", "threshold_change_rate", "comparison_minutes",
        "is_active", "severity", "created_at", "updated_at")}


def _validate(payload):
    payload.alert_type = payload.alert_type.upper()
    payload.severity = payload.severity.lower()
    if payload.alert_type not in {"OUT_OF_STOCK", "LOW_STOCK", "NEGATIVE_STOCK", "RAPID_DECREASE"}:
        raise HTTPException(400, "지원하지 않는 재고 경고 유형입니다.")
    if payload.severity not in {"info", "warning", "critical"}:
        raise HTTPException(400, "지원하지 않는 심각도입니다.")
    if payload.alert_type == "LOW_STOCK" and payload.threshold_quantity is None:
        raise HTTPException(400, "부족 재고 기준 수량이 필요합니다.")
    if payload.alert_type == "RAPID_DECREASE" and payload.threshold_change_quantity is None and payload.threshold_change_rate is None:
        raise HTTPException(400, "급감 수량 또는 비율 기준이 필요합니다.")


def _audit(db, request, user, row, action, summary):
    record_audit_log(db, request, user, action_type=action, menu_key="dashboard",
        menu_name="재고 경고 관리", target_type="inventory_alert_rule",
        target_id=row.id, target_name=row.name, action_summary=summary)


@router.get("/alert-rules")
def list_rules(db: Session = Depends(get_db)):
    return [_rule_dict(row) for row in db.query(InventoryAlertRule).order_by(InventoryAlertRule.id).all()]


@router.post("/alert-rules", status_code=201)
def create_rule(payload: RulePayload, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _validate(payload)
    row = InventoryAlertRule(**payload.dict())
    db.add(row); db.flush(); _audit(db, request, user, row, "create", "재고 경고 규칙을 생성했습니다."); db.commit(); db.refresh(row)
    return _rule_dict(row)


@router.put("/alert-rules/{rule_id}")
def update_rule(rule_id: int, payload: RulePayload, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _validate(payload); row = db.get(InventoryAlertRule, rule_id)
    if not row: raise HTTPException(404, "재고 경고 규칙을 찾을 수 없습니다.")
    for key, value in payload.dict().items(): setattr(row, key, value)
    _audit(db, request, user, row, "update", "재고 경고 규칙을 수정했습니다."); db.commit(); db.refresh(row)
    return _rule_dict(row)


@router.patch("/alert-rules/{rule_id}/active")
def set_rule_active(rule_id: int, payload: ActivePayload, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.get(InventoryAlertRule, rule_id)
    if not row: raise HTTPException(404, "재고 경고 규칙을 찾을 수 없습니다.")
    row.is_active = payload.is_active; _audit(db, request, user, row, "update", "재고 경고 규칙 활성 상태를 변경했습니다."); db.commit(); db.refresh(row)
    return _rule_dict(row)


@router.post("/alerts/run")
def run_alerts(db: Session = Depends(get_db)):
    latest = db.query(InventorySnapshot.snapshot_group_id).order_by(InventorySnapshot.snapshot_at.desc()).first()
    if not latest: raise HTTPException(400, "감지할 재고 스냅샷이 없습니다.")
    result = InventoryAlertService.detect_for_snapshot_group(db, latest[0]); db.commit(); return result


def _change_alert(alert_id, target, request, db, user):
    row = db.get(InventoryAlert, alert_id)
    if not row: raise HTTPException(404, "재고 경고를 찾을 수 없습니다.")
    from datetime import datetime, timezone
    row.status = target
    if target == "acknowledged": row.acknowledged_at, row.acknowledged_by = datetime.now(timezone.utc), user.id
    else: row.resolved_at = datetime.now(timezone.utc)
    record_audit_log(db, request, user, action_type="update", menu_key="dashboard", menu_name="재고 경고 관리", target_type="inventory_alert", target_id=row.id, target_name=row.item_name, action_summary="재고 경고 상태를 %s 처리했습니다." % target)
    db.commit(); return {"id": row.id, "status": row.status}


@router.patch("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _change_alert(alert_id, "acknowledged", request, db, user)


@router.patch("/alerts/{alert_id}/resolve")
def resolve(alert_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _change_alert(alert_id, "resolved", request, db, user)
