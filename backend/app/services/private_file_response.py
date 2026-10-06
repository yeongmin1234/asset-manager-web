"""Shared response policy for authenticated files stored under uploads."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Request
from fastapi.responses import FileResponse
from app.services.download_service import disposition


logger = logging.getLogger("app.private_files")
PRIVATE_FILE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, no-store",
}


def private_file_response(
    path: Path,
    *,
    request: Request,
    user_id: int,
    file_id: str,
    file_kind: str,
    media_type: str,
    filename: Optional[str] = None,
    inline: bool = False,
) -> FileResponse:
    logger.info(
        "private_file_access user_id=%s file_id=%s file_kind=%s at=%s ip=%s",
        user_id,
        file_id,
        file_kind,
        datetime.now(timezone.utc).isoformat(),
        request.client.host if request.client else "-",
    )
    headers = dict(PRIVATE_FILE_HEADERS)
    headers["Content-Disposition"] = disposition(filename, "inline" if inline else "attachment") if filename else ("inline" if inline else "attachment")
    return FileResponse(
        str(path),
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline" if inline else "attachment",
        headers=headers,
    )
