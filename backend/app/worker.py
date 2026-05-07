import os
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.job import Job
from app.services.video_service import video_service
from app.services.transcription_service import transcription_service
from app.services.clip_engine import clip_engine
from datetime import datetime
import threading

def process_video_job(project_id: str, db: Session):
    job = db.query(Job).filter(Job.project_id == project_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not job or not project:
        return

    try:
        job.state = "running"
        job.started_at = datetime.utcnow()
        job.progress = 10
        db.commit()

        # Step 1: Extract audio
        audio_path = os.path.join("storage", "temp", f"{project_id}.wav")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        job.progress = 20
        db.commit()
        video_service.extract_audio(project.filepath, audio_path)

        # Step 2: Transcribe
        job.progress = 40
        db.commit()
        segments = transcription_service.transcribe(audio_path)

        # Step 3: Select clips
        job.progress = 60
        db.commit()
        clips_metadata = clip_engine.select_clips(segments, project.prompt)

        # Step 4: Generate clips
        job.progress = 80
        db.commit()
        output_dir = os.path.join("storage", "clips", project_id)
        generated_clips = clip_engine.generate_clips(project.filepath, clips_metadata, output_dir)

        # Finalize
        project.clips = generated_clips
        project.status = "completed"
        job.state = "completed"
        job.progress = 100
        job.finished_at = datetime.utcnow()
        
        # Cleanup audio
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        db.commit()

    except Exception as e:
        print(f"Error processing project {project_id}: {e}")
        project.status = "failed"
        job.state = "failed"
        job.error = str(e)
        job.finished_at = datetime.utcnow()
        db.commit()

def start_processing(project_id: str, db_factory):
    """
    Start processing in a background thread.
    db_factory is a function that returns a new SessionLocal.
    """
    def run_with_db():
        db = db_factory()
        try:
            process_video_job(project_id, db)
        finally:
            db.close()

    thread = threading.Thread(target=run_with_db)
    thread.start()
