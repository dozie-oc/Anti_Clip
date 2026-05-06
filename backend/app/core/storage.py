"""Local JSON-file storage layer (simple, zero-dependency DB)."""
import json
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings


def ensure_storage_dirs() -> None:
    """Create all required storage directories on startup."""
    dirs = [
        settings.UPLOAD_DIR,
        os.path.join(settings.UPLOAD_DIR, "temp"),
        settings.CLIPS_DIR,
        os.path.dirname(settings.DB_FILE),
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(settings.DB_FILE):
        _write_raw({"projects": []})


def read_db() -> dict:
    """Read the full JSON database."""
    with open(settings.DB_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_db(data: dict) -> None:
    """Persist the full JSON database."""
    _write_raw(data)


def _write_raw(data: dict) -> None:
    with open(settings.DB_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)


def get_project_upload_dir(project_id: str) -> str:
    """Return (and create) the upload directory for a specific project."""
    path = os.path.join(settings.UPLOAD_DIR, project_id)
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def get_project_clips_dir(project_id: str) -> str:
    """Return (and create) the clips directory for a specific project."""
    path = os.path.join(settings.CLIPS_DIR, project_id)
    Path(path).mkdir(parents=True, exist_ok=True)
    return path
