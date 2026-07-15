from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.ecount_integration import EcountAuthTestResponse
from app.services.ecount_api_service import (
    EcountApiError,
    EcountApiService,
    EcountConfigurationError,
    EcountTimeoutError,
)
from app.schemas.inventory import AggregatedInventoryResponse
from app.services.inventory_service import InventoryError, InventoryService, InventoryTimeoutError


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
