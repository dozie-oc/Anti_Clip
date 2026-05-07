"""Upload route — POST /api/v1/upload"""
import os
import uuid

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.project import Project
from app.models.schemas import UploadResponse
from app.utils.validators import validate_file_size, validate_video_file

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    prompt: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Upload a video file and create a project in one step.
    The prompt can be set now or updated later before processing.
    """
    # 1. Validate extension
    await validate_video_file(file)

    # 2. Generate IDs and paths
    project_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    stored_name = f"{project_id}{ext}"

    # 3. Create project upload directory
    upload_dir = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, stored_name)

    # 4. Stream file to disk
    async with aiofiles.open(dest_path, "wb") as out_fh:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            await out_fh.write(chunk)

    # 5. Validate size after save
    validate_file_size(dest_path)
    file_size = os.path.getsize(dest_path)

    # 6. Create project record
    project = Project(
        id=project_id,
        name=file.filename.rsplit(".", 1)[0],  # filename without extension
        filename=stored_name,
        original_filename=file.filename,
        filepath=dest_path,
        file_size=file_size,
        prompt=prompt or "Find the most engaging moments",
        status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return UploadResponse(
        project_id=project_id,
        filename=stored_name,
        original_name=file.filename,
        size=file_size,
        message="Upload successful — project created",
    )
