"""
Clip engine — orchestrates LLM scoring and FFmpeg clip generation.

Pipeline:
  1. Receive merged transcript segments + user prompt
  2. Score segments via LLM service (batched)
  3. Select top-scoring segments above threshold
  4. Generate clips via FFmpeg
"""
import logging
import os
import uuid
from typing import List, Dict, Any

from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.video_service import video_service

logger = logging.getLogger(__name__)


class ClipEngine:
    """Scores transcript segments via LLM and generates video clips."""

    def select_clips(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        max_clips: int = None,
        score_threshold: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Score segments using the LLM service and select the best ones.

        Returns list of clip metadata:
        [{id, start, end, text, score, index}, ...]
        """
        max_clips = max_clips or settings.LLM_MAX_CLIPS
        score_threshold = score_threshold or settings.LLM_SCORE_THRESHOLD

        if not segments:
            logger.warning("No segments to score")
            return []

        # 1. Score all segments via LLM (batched)
        logger.info(f"Scoring {len(segments)} segments with prompt: '{user_prompt[:80]}...'")
        scored = llm_service.score_segments_batched(segments, user_prompt)

        # 2. Build a score map {index: score}
        score_map = {s["index"]: s["score"] for s in scored}

        # 3. Attach scores to segments and filter
        candidates = []
        for i, seg in enumerate(segments):
            score = score_map.get(i, 5)
            if score >= score_threshold:
                candidates.append({
                    "id": str(uuid.uuid4()),
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "score": score,
                    "index": i,
                })

        # 4. Sort by score descending, take top N
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:max_clips]

        # 5. Sort selected by timeline order for sequential clip generation
        selected.sort(key=lambda x: x["start"])

        logger.info(
            f"Selected {len(selected)} clips from {len(segments)} segments "
            f"(threshold={score_threshold}, max={max_clips})"
        )

        return selected

    def generate_clips(
        self,
        video_path: str,
        clips_metadata: List[Dict[str, Any]],
        output_dir: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate video clip files using FFmpeg.
        Returns updated clip metadata with file paths and URLs.
        """
        os.makedirs(output_dir, exist_ok=True)
        generated = []

        # Get total video duration for bounds checking
        total_duration = video_service.get_video_duration(video_path)

        for i, clip_meta in enumerate(clips_metadata):
            start = max(0, clip_meta["start"])
            end = clip_meta["end"]

            # Enforce minimum clip duration
            if end - start < settings.MIN_CLIP_DURATION:
                end = start + settings.MIN_CLIP_DURATION

            # Enforce maximum clip duration
            if end - start > settings.MAX_CLIP_DURATION:
                end = start + settings.MAX_CLIP_DURATION

            # Don't exceed video length
            if total_duration > 0 and end > total_duration:
                end = total_duration

            clip_id = clip_meta["id"]
            output_filename = f"clip_{i + 1:02d}_{clip_id[:8]}.mp4"
            output_path = os.path.join(output_dir, output_filename)

            try:
                video_service.cut_clip(video_path, start, end, output_path)

                generated.append({
                    "id": clip_id,
                    "filename": output_filename,
                    "path": output_path,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(end - start, 2),
                    "text": clip_meta["text"],
                    "score": clip_meta.get("score", 0),
                })

                logger.info(
                    f"Generated clip {i + 1}/{len(clips_metadata)}: "
                    f"{output_filename} ({start:.1f}s – {end:.1f}s, score={clip_meta.get('score', 0)})"
                )

            except Exception as e:
                logger.error(f"Failed to generate clip {clip_id}: {e}")
                continue

        return generated


# Module-level singleton
clip_engine = ClipEngine()
