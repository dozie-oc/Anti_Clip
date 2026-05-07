"""Projects routes — list, get, update, delete."""
import shutil
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.project import Project
from app.models.job import Job
from app.models.schemas import ProjectResponse, JobResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# List all projects
# ---------------------------------------------------------------------------

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """Return all projects, newest first."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects


# ---------------------------------------------------------------------------
# Get single project
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Return a single project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


# ---------------------------------------------------------------------------
# Update project prompt
# ---------------------------------------------------------------------------

@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    prompt: str = None,
    name: str = None,
    db: Session = Depends(get_db),
):
    """Update project prompt or name before processing."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail="Cannot update a project that is processing or completed.",
        )

    if prompt is not None:
        project.prompt = prompt
    if name is not None:
        project.name = name

    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)


# ---------------------------------------------------------------------------
# Get job status for a project
# ---------------------------------------------------------------------------

@router.get("/projects/{project_id}/job", response_model=JobResponse)
async def get_project_job(project_id: str, db: Session = Depends(get_db)):
    """Return the latest job for a project."""
    job = (
        db.query(Job)
        .filter(Job.project_id == project_id)
        .order_by(Job.started_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="No job found for this project.")
    return job


# ---------------------------------------------------------------------------
# Delete project
# ---------------------------------------------------------------------------

@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and all associated files."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Remove files from disk
    for base_dir in [settings.UPLOAD_DIR, settings.CLIPS_DIR]:
        folder = f"{base_dir}/{project_id}"
        if shutil.os.path.exists(folder):
            shutil.rmtree(folder)

    db.delete(project)
    db.commit()


# ---------------------------------------------------------------------------
# Reprocess a failed/completed project
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/reset")
async def reset_project(project_id: str, db: Session = Depends(get_db)):
    """Reset a failed/completed project back to pending so it can be reprocessed."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.status == "processing":
        raise HTTPException(status_code=409, detail="Project is currently processing.")

    # Clean up old clips
    clips_dir = f"{settings.CLIPS_DIR}/{project_id}"
    if shutil.os.path.exists(clips_dir):
        shutil.rmtree(clips_dir)

    project.status = "pending"
    project.processing_stage = None
    project.progress = 0
    project.error_message = None
    project.clips = []
    project.transcript = None
    db.commit()
    db.refresh(project)

    return ProjectResponse.model_validate(project)
