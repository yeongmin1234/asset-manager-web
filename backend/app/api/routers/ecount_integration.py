from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.ecount_integration import EcountAuthTestResponse
from app.services.ecount_api_service import (
    EcountApiError,
    EcountApiService,
    EcountConfigurationError,
    EcountTimeoutError,
)
from app.schemas.inventory import AggregatedInventoryResponse
from app.services.inventory_service import InventoryError, InventoryService, InventoryTimeoutError
from app.db.database import get_db
from fastapi import Depends
from app.models.inventory_job_run import InventoryJobRun
from app.models.inventory_schedule import InventorySchedule
from app.models.inventory_snapshot import InventorySnapshot
from app.schemas.inventory_snapshot import (
    InventoryJobRunRead,
    InventoryScheduleActiveRequest,
    InventoryScheduleCreate,
    InventoryScheduleRead,
    InventoryScheduleUpdate,
    InventorySnapshotAdminRead,
)
from app.services.inventory_scheduler_service import (
    apply_schedule_payload,
    calculate_next_run_at,
    refresh_inventory_scheduler,
)
from app.services.inventory_snapshot_service import (
    InventorySnapshotNotFoundError,
    InventorySnapshotService,
)


router = APIRouter(prefix="/admin/integrations/ecount", tags=["admin-integrations"])


@router.post("/test-auth", response_model=EcountAuthTestResponse)
def test_ecount_authentication() -> EcountAuthTestResponse:
    try:
        return EcountAuthTestResponse(**EcountApiService().test_connection().as_dict())
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except EcountTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except EcountApiError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc


@router.get("/inventory/test", response_model=AggregatedInventoryResponse)
def test_ecount_inventory(
    item_code: Optional[str] = Query(default=None, min_length=1, max_length=20),
    keyword: Optional[str] = Query(default=None),
    warehouse_code: Optional[str] = Query(default=None, max_length=5),
    base_date: Optional[str] = Query(default=None, min_length=8, max_length=8),
    limit: int = Query(default=50, ge=1, le=200),
) -> AggregatedInventoryResponse:
    try:
        if not item_code and not keyword:
            raise ValueError("검색할 품목명 또는 품목코드를 입력해주세요.")
        if item_code:
            result = InventoryService().get_aggregated_inventory(item_code, base_date, warehouse_code)
        else:
            result = InventoryService().search_inventory_by_keyword(keyword, base_date, warehouse_code, limit)
        return AggregatedInventoryResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc


@router.get("/inventory/schedules", response_model=List[InventoryScheduleRead])
def list_inventory_schedules(db: Session = Depends(get_db)):
    return list(db.scalars(select(InventorySchedule).order_by(InventorySchedule.id)))


@router.post("/inventory/schedules", response_model=InventoryScheduleRead, status_code=201)
def create_inventory_schedule(payload: InventoryScheduleCreate, db: Session = Depends(get_db)):
    _validate_schedule_target(payload.target_mode, payload.target_item_codes, payload.is_active)
    schedule = apply_schedule_payload(InventorySchedule(), payload)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    refresh_inventory_scheduler()
    return schedule


@router.put("/inventory/schedules/{schedule_id}", response_model=InventoryScheduleRead)
def update_inventory_schedule(
    schedule_id: int, payload: InventoryScheduleUpdate, db: Session = Depends(get_db),
):
    schedule = _get_schedule(db, schedule_id)
    _validate_schedule_target(payload.target_mode, payload.target_item_codes, payload.is_active)
    apply_schedule_payload(schedule, payload)
    db.commit()
    db.refresh(schedule)
    refresh_inventory_scheduler()
    return schedule


@router.patch("/inventory/schedules/{schedule_id}/active", response_model=InventoryScheduleRead)
def set_inventory_schedule_active(
    schedule_id: int, payload: InventoryScheduleActiveRequest, db: Session = Depends(get_db),
):
    schedule = _get_schedule(db, schedule_id)
    _validate_schedule_target(schedule.target_mode, schedule.target_item_codes, payload.is_active)
    schedule.is_active = payload.is_active
    schedule.next_run_at = calculate_next_run_at(schedule) if payload.is_active else None
    db.commit()
    db.refresh(schedule)
    refresh_inventory_scheduler()
    return schedule


@router.post("/inventory/schedules/{schedule_id}/run", response_model=InventoryJobRunRead)
def run_inventory_schedule(schedule_id: int, db: Session = Depends(get_db)):
    try:
        run = InventorySnapshotService().run_schedule(db, schedule_id, allow_inactive=True)
        if run.status == "skipped" and run.error_code == "duplicate_run":
            raise HTTPException(status_code=409, detail=run.safe_error_message)
        return run
    except InventorySnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/inventory/job-runs", response_model=List[InventoryJobRunRead])
def list_inventory_job_runs(
    schedule_id: Optional[int] = None,
    run_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(InventoryJobRun)
    if schedule_id is not None:
        query = query.where(InventoryJobRun.schedule_id == schedule_id)
    if run_status:
        query = query.where(InventoryJobRun.status == run_status)
    return list(db.scalars(query.order_by(InventoryJobRun.started_at.desc()).limit(limit)))


@router.get("/inventory/snapshots", response_model=List[InventorySnapshotAdminRead])
def list_inventory_snapshots(
    schedule_id: Optional[int] = None,
    item_code: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(InventorySnapshot)
    if schedule_id is not None:
        query = query.where(InventorySnapshot.schedule_id == schedule_id)
    if item_code:
        query = query.where(InventorySnapshot.item_code == item_code.strip().upper())
    return list(db.scalars(query.order_by(InventorySnapshot.snapshot_at.desc()).limit(limit)))


def _get_schedule(db, schedule_id):
    schedule = db.get(InventorySchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="재고 조회 일정을 찾을 수 없습니다.")
    return schedule


def _validate_schedule_target(target_mode, item_codes, is_active):
    if is_active and target_mode == "selected_items" and not item_codes:
        raise HTTPException(status_code=400, detail="활성 선택 품목 일정에는 품목코드가 필요합니다.")
