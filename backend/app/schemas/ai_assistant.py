from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    message: str


class AiChatResponse(BaseModel):
    success: bool
    intent: str
    message: str
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
