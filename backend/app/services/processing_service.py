"""
Processing service — simulates the AI clipping pipeline.

In production this would integrate with a real AI model (e.g. Whisper +
GPT-4 Vision / a custom video-segmentation model). For now it simulates
progress updates and writes placeholder clip metadata to the DB.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.storage import get_project_clips_dir, read_db, write_db
from app.models.schemas import GeneratedClip, ProjectStatus

logger = logging.getLogger(__name__)

# Map clip-length label → seconds
CLIP_DURATION_MAP = {"15s": 15.0, "30s": 30.0, "60s": 60.0}


async def run_processing_pipeline(project_id: str) -> None:
    """Background task: simulate clip generation with progress updates."""
    logger.info("Pipeline started for project %s", project_id)

    try:
        db = read_db()
        project = _find_project(db, project_id)
        if not project:
            logger.error("Project %s not found", project_id)
            return

        num_clips: int = project["settings"]["num_clips"]
        clip_length_label: str = project["settings"]["clip_length"]
        output_format: str = project["settings"]["output_format"]
        duration = CLIP_DURATION_MAP.get(clip_length_label, 30.0)
        clips_dir = get_project_clips_dir(project_id)

        for i in range(num_clips):
            # ── Simulate work ──────────────────────────────────────────────
            await asyncio.sleep(1.5)

            # ── Create placeholder clip entry ──────────────────────────────
            clip_id = str(uuid.uuid4())
            clip_filename = f"clip_{i + 1:03d}_{clip_id[:8]}.mp4"
            clip_path = os.path.join(clips_dir, clip_filename)

            # Write a tiny placeholder file so the path exists
            with open(clip_path, "wb") as fh:
                fh.write(b"")

            clip = GeneratedClip(
                id=clip_id,
                filename=clip_filename,
                path=clip_path,
                duration=duration,
                format=output_format,
            )

            # ── Persist progress ───────────────────────────────────────────
            db = read_db()
            project = _find_project(db, project_id)
            if not project:
                return

            project["clips"].append(clip.model_dump())
            project["progress"] = int(((i + 1) / num_clips) * 100)
            project["updated_at"] = datetime.utcnow().isoformat()
            write_db(db)

            logger.info(
                "Project %s — clip %d/%d done (%d%%)",
                project_id, i + 1, num_clips, project["progress"],
            )

        # ── Mark complete ──────────────────────────────────────────────────
        db = read_db()
        project = _find_project(db, project_id)
        if project:
            project["status"] = ProjectStatus.COMPLETED
            project["progress"] = 100
            project["updated_at"] = datetime.utcnow().isoformat()
            write_db(db)

        logger.info("Pipeline complete for project %s", project_id)

    except Exception as exc:  # pragma: no cover
        logger.exception("Pipeline failed for project %s: %s", project_id, exc)
        try:
            db = read_db()
            project = _find_project(db, project_id)
            if project:
                project["status"] = ProjectStatus.FAILED
                project["error_message"] = str(exc)
                project["updated_at"] = datetime.utcnow().isoformat()
                write_db(db)
        except Exception:
            pass


def _find_project(db: dict, project_id: str):
    """Return the mutable project dict from the DB (or None)."""
    for p in db.get("projects", []):
        if p["id"] == project_id:
            return p
    return None
