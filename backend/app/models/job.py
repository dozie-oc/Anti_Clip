from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from app.database import Base
import uuid
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    progress = Column(Integer, default=0)
    state = Column(String, default="queued")  # queued, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)
