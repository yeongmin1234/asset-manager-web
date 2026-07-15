from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.ai_assistant import (
    AiChatRequest,
    AiChatResponse,
    AiInventoryContextRequest,
    AiInventoryContextResponse,
)
from app.services.ai_assistant_service import AiAssistantService
from app.services.ai_inventory_context_service import save_inventory_context


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


@router.post("/chat", response_model=AiChatResponse)
def chat(
    payload: AiChatRequest,
    current_user: User = Depends(get_current_user),
) -> AiChatResponse:
    try:
        return AiChatResponse(**AiAssistantService().process_message(payload.message, current_user.id))
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
