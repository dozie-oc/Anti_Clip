"""Upload route — POST /api/v1/upload"""
import os
import uuid

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from typing import List

from app.core.config import settings
from app.models.schemas import UploadResponse
from app.utils.validators import validate_file_size, validate_video_file

router = APIRouter()

# In-process temp registry  {file_id: metadata_dict}
_temp_registry: dict[str, dict] = {}


@router.post("/upload", response_model=List[UploadResponse])
async def upload_files(files: List[UploadFile] = File(...)):
    """Receive one or more video files and stage them for project creation."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    results: List[UploadResponse] = []

    for file in files:
        # 1. Validate extension
        await validate_video_file(file)

        # 2. Build unique stored filename
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1].lower()
        stored_name = f"{file_id}{ext}"

        # 3. Write to temp directory
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        dest_path = os.path.join(temp_dir, stored_name)

        async with aiofiles.open(dest_path, "wb") as out_fh:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                await out_fh.write(chunk)

        # 4. Validate size (done post-save to avoid buffering entire file)
        validate_file_size(dest_path)

        file_size = os.path.getsize(dest_path)

        # 5. Register in temp store
        _temp_registry[file_id] = {
            "id": file_id,
            "filename": stored_name,
            "original_name": file.filename,
            "size": file_size,
            "path": dest_path,
        }

        results.append(
            UploadResponse(
                file_id=file_id,
                filename=stored_name,
                original_name=file.filename,
                size=file_size,
                message="Upload successful",
            )
        )

    return results


def get_temp_upload(file_id: str) -> dict | None:
    """Retrieve staged file metadata by ID."""
    return _temp_registry.get(file_id)


def clear_temp_upload(file_id: str) -> None:
    """Remove a file from the temp registry after project creation."""
    _temp_registry.pop(file_id, None)
