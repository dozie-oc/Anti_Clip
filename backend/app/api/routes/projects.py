"""Projects routes — CRUD for projects."""
import shutil
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.api.routes.upload import clear_temp_upload, get_temp_upload
from app.core.config import settings
from app.core.storage import read_db, write_db
from app.models.schemas import (
    CreateProjectRequest,
    Project,
    ProjectResponse,
    ProjectStatus,
    UploadedFile,
)
from app.services.file_service import move_temp_file_to_project

router = APIRouter()


# ---------------------------------------------------------------------------
# Create project
# ---------------------------------------------------------------------------

@router.post("/projects/create", response_model=ProjectResponse, status_code=201)
async def create_project(request: CreateProjectRequest):
    """Create a project by binding uploaded files to prompt + settings."""
    db = read_db()

    # Resolve staged files
    files: List[UploadedFile] = []
    project_id = str(uuid.uuid4())

    for file_id in request.file_ids:
        meta = get_temp_upload(file_id)
        if not meta:
            raise HTTPException(
                status_code=404,
                detail=f"Staged file '{file_id}' not found. Re-upload and try again.",
            )
        # Move from temp → project folder
        new_path = move_temp_file_to_project(
            meta["path"], project_id, meta["filename"]
        )
        files.append(
            UploadedFile(
                id=meta["id"],
                filename=meta["filename"],
                original_name=meta["original_name"],
                size=meta["size"],
                path=new_path,
            )
        )
        clear_temp_upload(file_id)

    name = request.name or f"Project — {datetime.utcnow().strftime('%b %d %Y, %H:%M')}"

    project = Project(
        id=project_id,
        name=name,
        prompt=request.prompt,
        settings=request.settings,
        files=files,
        status=ProjectStatus.READY,
    )

    db["projects"].insert(0, project.model_dump())
    write_db(db)
    return project


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """Return all projects, newest first."""
    db = read_db()
    return db["projects"]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Return a single project by ID."""
    db = read_db()
    project = _find(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """Delete a project and all its files."""
    db = read_db()
    project = _find(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Remove files from disk
    for base in [settings.UPLOAD_DIR, settings.CLIPS_DIR]:
        folder = f"{base}/{project_id}"
        if shutil.os.path.exists(folder):
            shutil.rmtree(folder)

    db["projects"] = [p for p in db["projects"] if p["id"] != project_id]
    write_db(db)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _find(db: dict, project_id: str):
    return next((p for p in db["projects"] if p["id"] == project_id), None)
