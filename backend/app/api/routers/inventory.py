from decimal import Decimal
import json
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.inventory import AggregatedInventoryResponse
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
    InventoryTimeoutError,
)
from app.services.inventory_analysis_service import InventoryAnalysisService
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.schemas.inventory_snapshot import (
    InventorySnapshotCompareResponse,
    InventorySnapshotGroupResponse,
    InventorySnapshotHistoryItem,
)
from app.services.inventory_snapshot_query_service import (
    compare_latest_snapshots,
    get_latest_snapshot,
    get_snapshot_history,
)


router = APIRouter(prefix="/inventory", tags=["inventory"])


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
        lambda: InventoryAnalysisService().analyze(
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
