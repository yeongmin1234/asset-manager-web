from fastapi import APIRouter, HTTPException, status

from app.schemas.ecount_integration import EcountAuthTestResponse
from app.services.ecount_api_service import (
    EcountApiError,
    EcountApiService,
    EcountConfigurationError,
    EcountTimeoutError,
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
