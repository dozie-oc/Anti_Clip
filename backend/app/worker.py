"""
Background worker — runs the full AI clipping pipeline in a separate thread.

Pipeline stages:
  1. audio_extraction  — FFmpeg extracts audio from video
  2. transcription     — Whisper transcribes audio to timestamped segments
  3. llm_analysis      — LLM scores segments against user prompt
  4. clip_generation   — FFmpeg cuts top-scoring segments into clips
"""
import logging
import os
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.job import Job
from app.services.video_service import video_service
from app.services.transcription_service import transcription_service
from app.services.clip_engine import clip_engine

logger = logging.getLogger(__name__)


def _update_job(db: Session, job: Job, **kwargs):
    """Helper to update job fields and commit."""
    for key, value in kwargs.items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)


def _update_project(db: Session, project: Project, **kwargs):
    """Helper to update project fields and commit."""
    for key, value in kwargs.items():
        setattr(project, key, value)
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)


def process_video_job(project_id: str, db: Session):
    """Execute the full AI clipping pipeline."""
    job = db.query(Job).filter(Job.project_id == project_id).order_by(Job.started_at.desc()).first()
    project = db.query(Project).filter(Project.id == project_id).first()

    if not job or not project:
        logger.error(f"Job or project not found for {project_id}")
        return

    try:
        # ── Mark running ──────────────────────────────────────────────────
        _update_job(db, job,
            state="running",
            started_at=datetime.utcnow(),
            progress=5,
            stage="audio_extraction",
            stage_detail="Preparing to extract audio...",
        )
        _update_project(db, project,
            status="processing",
            processing_stage="audio_extraction",
            progress=5,
        )

        # ── Stage 1: Extract audio ───────────────────────────────────────
        logger.info(f"[{project_id}] Stage 1: Audio extraction")
        audio_path = os.path.join("storage", "temp", f"{project_id}.wav")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        _update_job(db, job, progress=10, stage_detail="Extracting audio from video...")
        _update_project(db, project, progress=10)

        video_service.extract_audio(project.filepath, audio_path)

        _update_job(db, job, progress=25, stage_detail="Audio extraction complete")
        _update_project(db, project, progress=25)

        # ── Stage 2: Transcribe ──────────────────────────────────────────
        logger.info(f"[{project_id}] Stage 2: Transcription")
        _update_job(db, job,
            progress=30,
            stage="transcription",
            stage_detail="Transcribing audio with Whisper...",
        )
        _update_project(db, project,
            processing_stage="transcription",
            progress=30,
        )

        segments = transcription_service.transcribe_and_split(audio_path)

        # Store transcript on project
        transcript_data = [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in segments
        ]
        _update_project(db, project, transcript=transcript_data, progress=50)
        _update_job(db, job,
            progress=50,
            stage_detail=f"Transcription complete — {len(segments)} segments",
        )

        # ── Stage 3: LLM Analysis ───────────────────────────────────────
        logger.info(f"[{project_id}] Stage 3: LLM scoring")
        _update_job(db, job,
            progress=55,
            stage="llm_analysis",
            stage_detail="Analyzing segments with AI...",
        )
        _update_project(db, project,
            processing_stage="llm_analysis",
            progress=55,
        )

        clips_metadata = clip_engine.select_clips(segments, project.prompt)

        _update_job(db, job,
            progress=70,
            stage_detail=f"AI selected {len(clips_metadata)} clip candidates",
        )
        _update_project(db, project, progress=70)

        # ── Stage 4: Generate clips ─────────────────────────────────────
        logger.info(f"[{project_id}] Stage 4: Clip generation")
        _update_job(db, job,
            progress=75,
            stage="clip_generation",
            stage_detail="Generating video clips...",
        )
        _update_project(db, project,
            processing_stage="clip_generation",
            progress=75,
        )

        output_dir = os.path.join("storage", "clips", project_id)
        generated_clips = clip_engine.generate_clips(
            project.filepath, clips_metadata, output_dir
        )

        # Add URL paths for frontend access
        for clip in generated_clips:
            clip["url"] = f"/clips/{project_id}/{clip['filename']}"

        # ── Finalize ────────────────────────────────────────────────────
        _update_project(db, project,
            clips=generated_clips,
            status="completed",
            processing_stage=None,
            progress=100,
        )
        _update_job(db, job,
            state="completed",
            progress=100,
            stage="completed",
            stage_detail=f"Done — {len(generated_clips)} clips generated",
            finished_at=datetime.utcnow(),
        )

        # Cleanup temp audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up temp audio: {audio_path}")

        logger.info(f"[{project_id}] Pipeline complete — {len(generated_clips)} clips")

    except Exception as e:
        logger.exception(f"Pipeline failed for project {project_id}: {e}")
        try:
            _update_project(db, project,
                status="failed",
                error_message=str(e),
                processing_stage=None,
            )
            _update_job(db, job,
                state="failed",
                error=str(e),
                finished_at=datetime.utcnow(),
            )
        except Exception:
            logger.exception("Failed to update error state")


def start_processing(project_id: str, db_factory):
    """
    Launch the processing pipeline in a background thread.
    db_factory should be a callable that returns a new Session.
    """
    def run():
        db = db_factory()
        try:
            process_video_job(project_id, db)
        finally:
            db.close()

    thread = threading.Thread(target=run, name=f"worker-{project_id[:8]}")
    thread.daemon = True
    thread.start()
    logger.info(f"Started worker thread for project {project_id}")
