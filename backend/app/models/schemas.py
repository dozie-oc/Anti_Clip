"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProcessingMode(str, Enum):
    CLIPS = "clips"
    NARRATION_SUMMARY = "narration_summary"


# ---------------------------------------------------------------------------
# Clip metadata (stored as JSON in Project.clips)
# ---------------------------------------------------------------------------

class ClipMeta(BaseModel):
    id: str
    filename: str
    path: Optional[str] = None
    start: Optional[float] = 0.0
    end: Optional[float] = 0.0
    duration: Optional[float] = 0.0
    text: Optional[str] = ""
    score: Optional[int] = None
    url: Optional[str] = None



# ---------------------------------------------------------------------------
# Transcript segment
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class UploadAndCreateRequest(BaseModel):
    """Used after file upload to set prompt."""
    prompt: str = Field(..., min_length=1, max_length=5000)


class ProcessRequest(BaseModel):
    """Configuration for starting a processing job."""
    prompt: Optional[str] = None
    processing_mode: ProcessingMode = ProcessingMode.CLIPS
    clip_mode: str = "short"
    target_duration_minutes: Optional[int] = None
    num_output_videos: int = 1


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    project_id: str
    filename: str
    original_name: str
    size: int
    message: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    filename: str
    original_filename: str
    filepath: str
    file_size: int
    prompt: str
    clip_mode: str = "short"
    processing_mode: str = "clips"
    status: str
    processing_stage: Optional[str] = None
    progress: int
    error_message: Optional[str] = None
    clips: Optional[List[ClipMeta]] = []
    narration_script: Optional[str] = None
    transcript: Optional[List[TranscriptSegment]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


class JobResponse(BaseModel):
    id: str
    project_id: str
    progress: int
    state: str
    stage: Optional[str] = None
    stage_detail: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    target_duration_minutes: Optional[int] = None
    num_output_videos: int = 1
    narration_script: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessResponse(BaseModel):
    message: str
    project_id: str
    job_id: str


class HealthResponse(BaseModel):
    status: str
    whisper_model: str
    llm_model: str
    llm_configured: bool
