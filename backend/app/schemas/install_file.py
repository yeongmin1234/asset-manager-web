from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class InstallFileRead(BaseModel):
    id: int
    title: str
    category: str
    os_type: str
    version: Optional[str] = None
    description: Optional[str] = None
    install_guide: Optional[str] = None
    caution_note: Optional[str] = None
    original_filename: str
    file_size: int
    file_extension: str
    is_required: bool
    install_order: int
    download_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstallFileListResponse(BaseModel):
    items: List[InstallFileRead]
    total: int


class InstallFileSummary(BaseModel):
    total_count: int
    required_count: int
    total_size: int
    total_download_count: int


class InstallFileDeleteRequest(BaseModel):
    admin_password: str
