"""File validation utilities."""
import os
from fastapi import UploadFile, HTTPException
from app.core.config import settings


async def validate_video_file(file: UploadFile) -> None:
    """Validate file extension. Size is checked after save to avoid buffering."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type '{ext}' is not supported. "
                f"Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            ),
        )


def validate_file_size(path: str) -> None:
    """Validate file size after it has been saved to disk."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = os.path.getsize(path)
    if size > max_bytes:
        os.remove(path)
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
        )
