"""
Background worker — runs the full AI clipping or narration pipeline.
"""
import logging
import os
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.job import Job
from app.services.video_service import video_service
from app.services.scene_service import scene_service
from app.services.transcription_service import transcription_service
from app.services.clip_engine import clip_engine
from app.services.narration_engine import narration_engine

logger = logging.getLogger(__name__)


def _update_job(db: Session, job: Job, **kwargs):
    try:
        # Try to refresh, if it fails (ObjectDeletedError), try to re-fetch
        try:
            db.refresh(job)
        except:
            new_job = db.query(Job).filter(Job.id == job.id).first()
            if new_job:
                job = new_job
            else:
                return # Job is gone

        for key, value in kwargs.items():
            setattr(job, key, value)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update job: {e}")
        db.rollback()




def _update_project(db: Session, project: Project, **kwargs):
    try:
        try:
            db.refresh(project)
        except:
            new_project = db.query(Project).filter(Project.id == project.id).first()
            if new_project:
                project = new_project
            else:
                return

        for key, value in kwargs.items():
            setattr(project, key, value)
        project.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update project: {e}")
        db.rollback()



def _check_cancellation(db: Session, project_id: str):
    """Raise InterruptedError if project status is no longer 'processing'."""
    db.expire_all()  # Force refresh from DB
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p or p.status != "processing":
        logger.info(f"[{project_id}] Cancellation detected (status={p.status if p else 'deleted'})")
        raise InterruptedError("Processing stopped by user or project deleted.")



def process_video_job(project_id: str, db: Session):
    job = db.query(Job).filter(Job.project_id == project_id).order_by(Job.started_at.desc()).first()
    project = db.query(Project).filter(Project.id == project_id).first()

    if not job or not project:
        return

    mode = getattr(project, "processing_mode", "clips")
    logger.info(f"[{project_id}] Starting pipeline in {mode} mode")

    try:
        # ── Stage 1: Processing ──────────────────────────────────────────
        _update_job(db, job, state="running", stage="processing", progress=5, started_at=datetime.utcnow())
        _update_project(db, project, status="processing", processing_stage="processing", progress=5)

        # Audio + Scenes
        audio_path = os.path.join("storage", "temp", f"{project_id}.wav")
        video_service.extract_audio(project.filepath, audio_path)
        _check_cancellation(db, project_id)
        scenes = scene_service.detect_scenes(project.filepath)
        _check_cancellation(db, project_id)


        # ── Stage 2: Transcribing ────────────────────────────────────────
        _update_job(db, job, stage="transcribing", progress=30, stage_detail="Transcribing and aligning...")
        _update_project(db, project, processing_stage="transcribing", progress=30)
        
        raw_segments = transcription_service.transcribe(audio_path)
        _check_cancellation(db, project_id)
        segments = transcription_service.align_segments_to_scenes(raw_segments, scenes)
        _update_project(db, project, transcript=segments)
        _check_cancellation(db, project_id)


        # ── Stage 3: Mode-specific Analysis & Generation ─────────────────
        output_dir = os.path.join("storage", "clips", project_id)
        os.makedirs(output_dir, exist_ok=True)

        if mode == "narration_summary":
            _update_job(db, job, stage="analyzing", progress=55, stage_detail="Generating narration script...")
            _update_project(db, project, processing_stage="analyzing", progress=55)
            # Combine all text for narration input
            full_text = " ".join([s["text"] for s in segments])
            target_min = job.target_duration_minutes or 5
            
            summary_results = narration_engine.process_narration_mode(
                project_id, full_text, target_min, project.filepath, output_dir
            )
            
            # Update project and job with the script
            script_text = summary_results[0]["script"]
            project.narration_script = script_text
            _update_job(db, job, narration_script=script_text)
            
            # In narration mode, 'clips' are the generated summaries
            generated_clips = summary_results
        else:
            # CLIPS MODE
            _update_job(db, job, stage="analyzing", progress=55, stage_detail="Scoring viral clips...")
            _update_project(db, project, processing_stage="analyzing", progress=55)

            def progress_cb(prog, detail):
                _update_job(db, job, progress=prog, stage_detail=detail)
                _update_project(db, project, progress=prog)

            clips_metadata = clip_engine.select_clips(
                segments, project.prompt, clip_mode=project.clip_mode, progress_callback=progress_cb
            )
            
            _update_job(db, job, stage="clipping", progress=75, stage_detail="Rendering vertical clips...")
            _update_project(db, project, processing_stage="clipping", progress=75)
            generated_clips = clip_engine.generate_clips(
                project.filepath, clips_metadata, output_dir, clip_mode=project.clip_mode
            )

        # Add URL paths
        for clip in generated_clips:
            if "filename" in clip:
                clip["url"] = f"/clips/{project_id}/{clip['filename']}"

        # ── Finalize ────────────────────────────────────────────────────
        _update_project(db, project, clips=generated_clips, status="completed", processing_stage=None, progress=100)
        _update_job(db, job, state="completed", progress=100, stage="completed", finished_at=datetime.utcnow())

        if os.path.exists(audio_path):
            os.remove(audio_path)

    except InterruptedError as e:
        logger.info(f"Pipeline stopped: {e}")
        # Job and project status should already be handled by the stopper, 
        # but we'll ensure the job is marked as failed/stopped.
        _update_job(db, job, state="failed", error="Stopped by user", finished_at=datetime.utcnow())
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        _update_project(db, project, status="failed", error_message=str(e), processing_stage=None)
        _update_job(db, job, state="failed", error=str(e), finished_at=datetime.utcnow())



def start_processing(project_id: str, db_factory):
    def run():
        db = db_factory()
        try:
            process_video_job(project_id, db)
        finally:
            db.close()
    threading.Thread(target=run, daemon=True).start()
