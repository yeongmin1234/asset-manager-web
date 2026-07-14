import re
from typing import Dict

from pydantic import BaseModel, Field, field_validator


class SidebarMenuLabelUpdate(BaseModel):
    menu_name: str = Field(..., min_length=1, max_length=30)

    @field_validator("menu_name")
    @classmethod
    def normalize_menu_name(cls, value: str) -> str:
        normalized = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip()
        if not normalized:
            raise ValueError("메뉴 이름을 입력해주세요.")
        if re.search(r"<[^>]*>|javascript\s*:|script", normalized, re.IGNORECASE):
            raise ValueError("HTML 또는 스크립트 문자열은 사용할 수 없습니다.")
        return normalized


class SidebarMenuLabelsResponse(BaseModel):
    labels: Dict[str, str]
