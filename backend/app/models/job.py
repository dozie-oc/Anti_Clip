"""Job ORM model — tracks processing pipeline state."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    progress = Column(Integer, default=0)
    state = Column(String, default="queued")  # queued, running, completed, failed
    stage = Column(String, nullable=True)  # audio_extraction, transcription, llm_analysis, clip_generation
    stage_detail = Column(String, nullable=True)  # human-readable detail of current stage
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    # Narration summary mode fields
    target_duration_minutes = Column(Integer, nullable=True)  # desired output length
    num_output_videos = Column(Integer, default=1)
    narration_script = Column(Text, nullable=True)  # AI-generated narration text

    # Relationship
    project = relationship("Project", back_populates="jobs")
