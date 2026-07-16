from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class AiChatResponse(BaseModel):
    success: bool
    intent: str
    message: str
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


class AiInventoryContextRequest(BaseModel):
    intent: str
    query: str
    items: List[Dict[str, Any]] = Field(min_length=1)
    threshold: Optional[int] = None
    searched_at: Optional[str] = None
    selected_item_code: Optional[str] = None


class AiInventoryContextResponse(BaseModel):
    success: bool
