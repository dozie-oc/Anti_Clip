"""Process route — start the AI clipping pipeline for a project."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.project import Project
from app.models.job import Job
from app.models.schemas import ProcessResponse
from app.worker import start_processing

router = APIRouter()


@router.post("/projects/{project_id}/process", response_model=ProcessResponse)
async def start_processing_route(
    project_id: str,
    prompt: str = None,
    db: Session = Depends(get_db),
):
    """
    Kick off the background AI clipping pipeline for a project.
    Optionally update the prompt before processing starts.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status == "processing":
        raise HTTPException(status_code=409, detail="Project is already being processed.")

    # Optionally update prompt
    if prompt:
        project.prompt = prompt

    # Reset project state for (re)processing
    project.status = "processing"
    project.processing_stage = "queued"
    project.progress = 0
    project.clips = []
    project.error_message = None

    # Create a new job record
    job = Job(project_id=project_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    db.refresh(project)

    # Start background worker thread with its own DB session
    start_processing(project_id, SessionLocal)

    return ProcessResponse(
        message="Processing started.",
        project_id=project_id,
        job_id=job.id,
    )
