from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.ai_assistant import (
    AiChatRequest,
    AiChatResponse,
    AiInventoryContextRequest,
    AiInventoryContextResponse,
)
from app.services.ai_assistant_service import AiAssistantPermissionError, AiAssistantService
from app.services.ai_inventory_context_service import save_inventory_context
from app.services.ecount_api_service import EcountConfigurationError
from app.services.inventory_service import InventoryError, InventoryRateLimitError, InventoryTimeoutError


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


@router.post("/chat", response_model=AiChatResponse)
def chat(
    payload: AiChatRequest,
    current_user: User = Depends(get_current_user),
) -> AiChatResponse:
    try:
        return AiChatResponse(**AiAssistantService().process_message(
            payload.message, current_user.id, current_user, context=payload.context,
        ))
    except AiAssistantPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 기능을 사용할 권한이 없습니다.") from exc
    except InventoryRateLimitError as exc:
        retry_after = max(1, int(exc.retry_after_seconds or 60))
        message = "이카운트 요청 제한으로 약 {}초 후 다시 조회할 수 있습니다.".format(retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "intent": "inventory_search",
                "message": message,
                "data": {
                    "type": "rate_limited",
                    "retry_after_seconds": retry_after,
                },
                "suggestions": [],
            },
            headers={
                "Retry-After": str(retry_after),
                "X-Inventory-Error-Code": "ECOUNT_RATE_LIMITED",
            },
        )
    except InventoryTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc
    except EcountConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message) from exc
    except InventoryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="질문 처리 중 오류가 발생했습니다.",
        ) from exc


@router.post("/inventory-context", response_model=AiInventoryContextResponse)
def update_inventory_context(
    payload: AiInventoryContextRequest,
    current_user: User = Depends(get_current_user),
) -> AiInventoryContextResponse:
    save_inventory_context(
        user_id=current_user.id,
        intent=payload.intent,
        query=payload.query,
        items=payload.items,
        threshold=payload.threshold,
        searched_at=payload.searched_at,
        selected_item_code=payload.selected_item_code,
    )
    return AiInventoryContextResponse(success=True)
