from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.inventory import AggregatedInventoryResponse
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import (
    InventoryError,
    InventoryService,
    InventoryTimeoutError,
)


router = APIRouter(prefix="/inventory", tags=["inventory"])


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
