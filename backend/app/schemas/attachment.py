from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.attachment import AttachmentEntityType


class AttachmentRead(BaseModel):
    id: int
    entity_type: AttachmentEntityType
    entity_id: int
    original_filename: str
    mime_type: Optional[str] = None
    file_size: int
    description: Optional[str] = None
    created_at: datetime
    uploader_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
