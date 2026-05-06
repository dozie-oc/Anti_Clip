"""Pydantic schemas for requests, responses, and internal models."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ClipLength(str, Enum):
    SHORT = "15s"
    MEDIUM = "30s"
    LONG = "60s"


class OutputFormat(str, Enum):
    SHORTS = "shorts"
    TIKTOK = "tiktok"
    LANDSCAPE = "landscape"


class ProjectStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class UploadedFile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_name: str
    size: int
    path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectSettings(BaseModel):
    clip_length: ClipLength = ClipLength.SHORT
    output_format: OutputFormat = OutputFormat.SHORTS
    num_clips: int = Field(default=5, ge=1, le=50)


class GeneratedClip(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    path: str
    duration: float
    format: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    prompt: str
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    files: List[UploadedFile] = []
    clips: List[GeneratedClip] = []
    status: ProjectStatus = ProjectStatus.PENDING
    progress: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Request / Response bodies
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    file_ids: List[str]
    name: Optional[str] = None


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    original_name: str
    size: int
    message: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    prompt: str
    settings: ProjectSettings
    files: List[UploadedFile]
    clips: List[GeneratedClip]
    status: ProjectStatus
    progress: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class ProcessResponse(BaseModel):
    message: str
    project_id: str
