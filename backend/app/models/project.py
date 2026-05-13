"""Project ORM model."""
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    prompt = Column(Text, nullable=False)
    clip_mode = Column(String, default="short")  # "short" or "long"
    processing_mode = Column(String, default="clips")  # "clips" or "narration_summary"
    status = Column(String, default="pending")  # pending, processing, completed, failed
    processing_stage = Column(String, nullable=True)  # audio_extraction, transcription, llm_analysis, clip_generation
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    transcript = Column(JSON, nullable=True)  # Full transcript segments
    clips = Column(JSON, default=list)  # List of generated clip metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
