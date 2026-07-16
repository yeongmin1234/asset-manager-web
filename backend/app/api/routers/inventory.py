from decimal import Decimal
import json
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user, require_menu_permission
from app.models.user import User
from app.schemas.inventory import (
    AggregatedInventoryResponse, ProductMasterListResponse,
    WarehouseInventoryResponse, WarehouseMasterListResponse,
)
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import (
    InventoryError,
    InventoryRateLimitError,
    InventoryService,
    InventoryTimeoutError,
)
from app.services.inventory_analysis_service import (
    InventoryAnalysisService,
    InventorySnapshotUnavailableError,
)
from app.db.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.schemas.inventory_snapshot import (
    InventorySnapshotCompareResponse,
    InventorySnapshotGroupResponse,
    InventorySnapshotHistoryItem,
    InventoryChangeResponse,
)
from app.services.inventory_snapshot_query_service import (
    compare_latest_snapshots,
    get_latest_snapshot,
    get_snapshot_history,
)
from app.services.inventory_change_analysis_service import InventoryChangeAnalysisService
from app.services.warehouse_inventory_service import WarehouseInventoryService
from app.models.inventory_alert import InventoryAlert


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/warehouses", response_model=WarehouseMasterListResponse)
def list_inventory_warehouses(
    keyword: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> WarehouseMasterListResponse:
    try:
        return WarehouseMasterListResponse(**WarehouseInventoryService(db=db).list_warehouses(keyword, limit, offset))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="창고 목록을 불러올 수 없습니다.") from exc


@router.get("/warehouses/{warehouse_code}/inventory", response_model=WarehouseInventoryResponse)
def read_warehouse_inventory(
    warehouse_code: str,
    keyword: Optional[str] = Query(default=None, max_length=200),
    include_zero: bool = Query(default=False),
    sort_by: str = Query(default="quantity_desc", alias="sort"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> WarehouseInventoryResponse:
    try:
        result = WarehouseInventoryService().get_warehouse_inventory(
            warehouse_code, keyword, include_zero, sort_by, limit, offset,
        )
        return WarehouseInventoryResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InventoryRateLimitError as exc:
        retry_after = max(1, int(exc.retry_after_seconds or 60))
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="이카운트 요청 제한으로 약 {}초 후 다시 조회할 수 있습니다.".format(retry_after), headers={"Retry-After": str(retry_after)}) from exc
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc


@router.get("/products", response_model=ProductMasterListResponse)
def list_inventory_products(
    keyword: Optional[str] = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> ProductMasterListResponse:
    try:
        return ProductMasterListResponse(**InventoryService().list_products(
            keyword=keyword, page=page, page_size=page_size,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc


def _alert_item(row):
    return {
        "id": row.id, "alert_type": row.alert_type, "severity": row.severity,
        "status": row.status, "item_code": row.item_code, "item_name": row.item_name,
        "current_quantity": row.current_quantity, "total_quantity": row.current_quantity,
        "previous_quantity": row.previous_quantity, "change_quantity": row.change_quantity,
        "change_rate": row.change_rate, "threshold": row.threshold_description,
        "detected_at": row.detected_at, "safe_message": row.safe_message,
        "partial_result": row.partial_result, "warehouses": [],
    }


@router.get("/alerts")
def read_inventory_alerts(
    alert_status: Optional[str] = Query(default="active", alias="status"),
    alert_type: Optional[str] = None, severity: Optional[str] = None,
    item_code: Optional[str] = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=200), db: Session = Depends(get_db),
    _=Depends(require_menu_permission("dashboard")),
):
    query = db.query(InventoryAlert)
    if alert_status:
        query = query.filter(InventoryAlert.status == alert_status)
    if alert_type:
        query = query.filter(InventoryAlert.alert_type == alert_type.upper())
    if severity:
        query = query.filter(InventoryAlert.severity == severity.lower())
    if item_code:
        query = query.filter(InventoryAlert.item_code == item_code.strip())
    rows = query.order_by(InventoryAlert.detected_at.desc()).limit(limit).all()
    return {"total": len(rows), "items": [_alert_item(row) for row in rows], "mode": "inventory_alert"}


@router.get("/alerts/summary")
def read_inventory_alert_summary(
    db: Session = Depends(get_db), _=Depends(require_menu_permission("dashboard")),
):
    rows = db.query(InventoryAlert).filter(InventoryAlert.status == "active").all()
    counts = {key: 0 for key in ("OUT_OF_STOCK", "LOW_STOCK", "NEGATIVE_STOCK", "RAPID_DECREASE")}
    for row in rows:
        counts[row.alert_type] = counts.get(row.alert_type, 0) + 1
    return {
        "active_total": len(rows), "out_of_stock": counts["OUT_OF_STOCK"],
        "low_stock": counts["LOW_STOCK"], "negative_stock": counts["NEGATIVE_STOCK"],
        "rapid_decrease": counts["RAPID_DECREASE"],
        "items": [_alert_item(row) for row in rows[:200]], "mode": "inventory_alert",
    }


@router.get("/analysis/compare", response_model=InventoryChangeResponse)
def analyze_inventory_change(
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    item_code: Optional[str] = Query(default=None, max_length=20),
    keyword: Optional[str] = Query(default=None, max_length=200),
    schedule_id: Optional[int] = None,
    start_schedule_id: Optional[int] = None,
    end_schedule_id: Optional[int] = None,
    direction: str = Query(default="all"),
    extreme: Optional[str] = Query(default=None),
    mode: str = Query(default="latest_previous"),
    today_only: bool = False,
    limit: int = Query(default=200, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_menu_permission("dashboard")),
):
    try:
        return InventoryChangeAnalysisService().compare(
            db, start_at=start_at, end_at=end_at, item_code=item_code, keyword=keyword,
            schedule_id=schedule_id, start_schedule_id=start_schedule_id,
            end_schedule_id=end_schedule_id, direction=direction, mode=mode,
            extreme=extreme, today_only=today_only, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analysis/summary", response_model=InventoryChangeResponse)
def summarize_inventory_change(
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    item_code: Optional[str] = Query(default=None, max_length=20),
    keyword: Optional[str] = Query(default=None, max_length=200),
    schedule_id: Optional[int] = None,
    start_schedule_id: Optional[int] = None,
    end_schedule_id: Optional[int] = None,
    mode: str = Query(default="latest_previous"),
    today_only: bool = False,
    limit: int = Query(default=200, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_menu_permission("dashboard")),
):
    try:
        return InventoryChangeAnalysisService().summary(
            db, start_at=start_at, end_at=end_at, item_code=item_code, keyword=keyword,
            schedule_id=schedule_id, start_schedule_id=start_schedule_id,
            end_schedule_id=end_schedule_id, mode=mode, today_only=today_only, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/snapshots/latest", response_model=InventorySnapshotGroupResponse)
def read_latest_inventory_snapshot(
    item_code: Optional[str] = Query(default=None, max_length=20),
    keyword: Optional[str] = Query(default=None, max_length=200),
    schedule_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return get_latest_snapshot(db, item_code=item_code, keyword=keyword, schedule_id=schedule_id)


@router.get("/snapshots/history", response_model=List[InventorySnapshotHistoryItem])
def read_inventory_snapshot_history(
    item_code: Optional[str] = Query(default=None, max_length=20),
    keyword: Optional[str] = Query(default=None, max_length=200),
    snapshot_date: Optional[date] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    schedule_id: Optional[int] = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return get_snapshot_history(
        db, item_code=item_code, keyword=keyword, snapshot_date=snapshot_date,
        start_at=start_at, end_at=end_at, schedule_id=schedule_id, limit=limit,
    )


@router.get("/snapshots/compare", response_model=InventorySnapshotCompareResponse)
def compare_inventory_snapshots(
    item_code: Optional[str] = Query(default=None, max_length=20),
    keyword: Optional[str] = Query(default=None, max_length=200),
    schedule_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return compare_latest_snapshots(db, item_code=item_code, keyword=keyword, schedule_id=schedule_id)


@router.get("/analyze", response_model=AggregatedInventoryResponse)
def analyze_inventory(
    intent: str = Query(...),
    queries: Optional[str] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    comparison: Optional[str] = Query(default=None),
    threshold: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AggregatedInventoryResponse:
    parsed_queries = None
    if queries:
        try:
            value = json.loads(queries)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError
            parsed_queries = value
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="비교 품목 형식이 올바르지 않습니다.") from exc
    return _run_inventory_query(
        lambda: InventoryAnalysisService(db=db).analyze(
            intent=intent,
            user_id=current_user.id,
            queries=parsed_queries,
            direction=direction,
            comparison=comparison,
            threshold=threshold,
        )
    )


@router.get("/search", response_model=AggregatedInventoryResponse)
def search_inventory(
    item_code: Optional[str] = Query(default=None, min_length=1, max_length=20),
    keyword: Optional[str] = Query(default=None),
    warehouse_code: Optional[str] = Query(default=None, max_length=5),
    base_date: Optional[str] = Query(default=None, min_length=8, max_length=8),
    limit: int = Query(default=50, ge=1, le=200),
) -> AggregatedInventoryResponse:
    if not item_code and not keyword:
        raise HTTPException(status_code=400, detail="검색할 품목명 또는 품목코드를 입력해주세요.")
    if item_code:
        operation = lambda: InventoryService().get_aggregated_inventory(
            item_code, base_date, warehouse_code,
        )
    else:
        operation = lambda: InventoryService().search_inventory_by_keyword(
            keyword, base_date, warehouse_code, limit,
        )
    return _run_inventory_query(operation)


@router.get("/low-stock", response_model=AggregatedInventoryResponse)
def get_low_stock_inventory(
    item_code: Optional[str] = Query(default=None, min_length=1, max_length=20),
    keyword: Optional[str] = Query(default=None),
    threshold: Decimal = Query(default=Decimal("10"), ge=0, le=Decimal("1000000000")),
    warehouse_code: Optional[str] = Query(default=None, max_length=5),
    limit: int = Query(default=100, ge=1, le=200),
) -> AggregatedInventoryResponse:
    return _run_inventory_query(
        lambda: InventoryService().get_aggregated_low_stock(
            keyword=keyword,
            item_code=item_code,
            threshold=threshold,
            warehouse_code=warehouse_code,
            limit=limit,
        )
    )


def _run_inventory_query(operation) -> AggregatedInventoryResponse:
    try:
        return AggregatedInventoryResponse(**operation())
    except InventorySnapshotUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except InventoryRateLimitError as exc:
        retry_after = max(1, int(exc.retry_after_seconds or 60))
        message = "이카운트 요청 제한으로 약 {}초 후 다시 조회할 수 있습니다.".format(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": message,
                "error_code": "ECOUNT_RATE_LIMITED",
                "retry_after_seconds": retry_after,
                "data": {"type": "rate_limited"},
            },
            headers={
                "Retry-After": str(retry_after),
                "X-Inventory-Error-Code": "ECOUNT_RATE_LIMITED",
            },
        ) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
