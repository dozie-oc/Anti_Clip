"""Process route — start the AI clipping pipeline for a project."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models.project import Project
from app.models.job import Job
from app.models.schemas import ProcessRequest, ProcessResponse
from app.worker import start_processing

router = APIRouter()


@router.post("/projects/{project_id}/process", response_model=ProcessResponse)
async def start_processing_route(
    project_id: str,
    body: ProcessRequest = Body(default=ProcessRequest()),
    db: Session = Depends(get_db),
):
    """
    Kick off the background processing pipeline for a project.
    Supports both 'clips' and 'narration_summary' modes.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status == "processing":
        raise HTTPException(status_code=409, detail="Project is already being processed.")

    # Update project settings from request
    if body.prompt:
        project.prompt = body.prompt
    project.processing_mode = body.processing_mode.value
    project.clip_mode = body.clip_mode

    # Reset project state for (re)processing
    project.status = "processing"
    project.processing_stage = "queued"
    project.progress = 0
    project.clips = []
    project.error_message = None

    # Create a new job record with mode-specific fields
    job = Job(
        project_id=project_id,
        target_duration_minutes=body.target_duration_minutes,
        num_output_videos=body.num_output_videos,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.refresh(project)

    # Start background worker thread with its own DB session
    start_processing(project_id, SessionLocal)

    return ProcessResponse(
        message=f"Processing started ({body.processing_mode.value} mode).",
        project_id=project_id,
        job_id=job.id,
    )


@router.post("/projects/{project_id}/stop")
async def stop_processing_route(
    project_id: str,
    db: Session = Depends(get_db),
):
    """
    Stop a running processing pipeline.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status != "processing":
        return {"message": "Project is not currently processing.", "project_id": project_id}

    # Set status to something else to trigger cancellation in worker
    project.status = "pending"
    project.processing_stage = None
    project.progress = 0
    
    # Also find the running job and mark it
    job = db.query(Job).filter(Job.project_id == project_id, Job.state == "running").first()
    if job:
        job.state = "failed"
        job.error = "Stopped by user"
        job.finished_at = datetime.utcnow()

    db.commit()
    return {"message": "Processing stop signal sent.", "project_id": project_id}

