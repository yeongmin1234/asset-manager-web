from typing import Dict

from pydantic import BaseModel


class MenuVisibilityUpdate(BaseModel):
    visible: bool


class MenuVisibilityResponse(BaseModel):
    visibility: Dict[str, bool]
