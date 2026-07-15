from fastapi import APIRouter, HTTPException, status

from app.schemas.ai_assistant import AiChatRequest, AiChatResponse
from app.services.ai_assistant_service import AiAssistantService


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


@router.post("/chat", response_model=AiChatResponse)
def chat(payload: AiChatRequest) -> AiChatResponse:
    try:
        return AiChatResponse(**AiAssistantService().process_message(payload.message))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="질문 처리 중 오류가 발생했습니다.",
        ) from exc
