"""Process route — start the clipping pipeline for a project."""
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.storage import read_db, write_db
from app.models.schemas import ProcessResponse, ProjectStatus
from app.services.processing_service import run_processing_pipeline
from datetime import datetime

router = APIRouter()


@router.post("/projects/{project_id}/process", response_model=ProcessResponse)
async def start_processing(project_id: str, background_tasks: BackgroundTasks):
    """Kick off background clip generation for a project."""
    db = read_db()
    project = next((p for p in db["projects"] if p["id"] == project_id), None)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project["status"] == ProjectStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Project is already being processed.")

    if project["status"] == ProjectStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Project has already been processed.")

    # Set initial processing state
    project["status"] = ProjectStatus.PROCESSING
    project["progress"] = 0
    project["clips"] = []
    project["error_message"] = None
    project["updated_at"] = datetime.utcnow().isoformat()
    write_db(db)

    background_tasks.add_task(run_processing_pipeline, project_id)

    return ProcessResponse(message="Processing started.", project_id=project_id)
