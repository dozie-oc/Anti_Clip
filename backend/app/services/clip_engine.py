"""
Clip engine — orchestrates LLM scoring and FFmpeg clip generation.

Pipeline:
  1. Receive merged transcript segments + user prompt + clip_mode
  2. Score segments via LLM service (batched, mode-aware)
  3. Blend with heuristic scores (75/25 hybrid)
  4. Select top-scoring segments above threshold
  5. Generate clips via FFmpeg with mode-appropriate duration limits
"""
import logging
import os
import uuid
from typing import List, Dict, Any

from app.core.config import settings
from app.services.llm_service import llm_service, FallbackProvider
from app.services.video_service import video_service

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Mode profiles — duration and scoring parameters per clip mode
# ═══════════════════════════════════════════════════════════════════════════

MODE_PROFILES = {
    "short": {
        "segment_duration": 15.0,   # Whisper merge target (seconds)
        "min_clip": 5.0,
        "max_clip": 60.0,
        "score_threshold": 6,
        "max_clips": 10,
    },
    "long": {
        "segment_duration": 45.0,   # Wider context for narrative arcs
        "min_clip": 30.0,
        "max_clip": 180.0,
        "score_threshold": 5,       # Wider net — fewer candidates anyway
        "max_clips": 6,
    },
}


def get_mode_profile(clip_mode: str) -> dict:
    """Return the mode profile, defaulting to 'short'."""
    return MODE_PROFILES.get(clip_mode, MODE_PROFILES["short"])


class ClipEngine:
    """Scores transcript segments via LLM and generates video clips."""

    def select_clips(
        self,
        segments: List[Dict[str, Any]],
        user_prompt: str,
        clip_mode: str = "short",
        max_clips: int = None,
        score_threshold: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Score segments using the LLM, optionally blend with heuristics,
        and select the best clips.

        Returns list of clip metadata:
        [{id, start, end, text, score, index}, ...]
        """
        profile = get_mode_profile(clip_mode)
        max_clips = max_clips or profile["max_clips"]
        score_threshold = score_threshold or profile["score_threshold"]

        if not segments:
            logger.warning("No segments to score")
            return []

        # ── 1. LLM scores (batched) ──────────────────────────────────────
        logger.info(
            f"Scoring {len(segments)} segments "
            f"[mode={clip_mode}, prompt='{user_prompt[:60]}...']"
        )
        scored = llm_service.score_segments_batched(
            segments, user_prompt, clip_mode=clip_mode
        )
        llm_map = {s["index"]: s["score"] for s in scored}

        # ── 2. Hybrid blending (75% LLM + 25% heuristic) ────────────────
        use_hybrid = not isinstance(llm_service.provider, FallbackProvider)

        heuristic_map = {}
        if use_hybrid:
            heuristic = FallbackProvider().score_segments(
                segments, user_prompt, clip_mode=clip_mode
            )
            heuristic_map = {s["index"]: s["score"] for s in heuristic}
            logger.info("Applying hybrid scoring (75% LLM + 25% heuristic)")

        # ── 3. Build candidates with blended scores ──────────────────────
        candidates = []
        for i, seg in enumerate(segments):
            llm_score = llm_map.get(i, 5)

            if use_hybrid:
                heur_score = heuristic_map.get(i, 5)
                final_score = round(llm_score * 0.75 + heur_score * 0.25)
            else:
                final_score = llm_score

            if final_score >= score_threshold:
                candidates.append({
                    "id": str(uuid.uuid4()),
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "score": final_score,
                    "index": i,
                })

        # ── 4. Sort by score descending, take top N ──────────────────────
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:max_clips]

        # ── 5. Sort selected by timeline order ───────────────────────────
        selected.sort(key=lambda x: x["start"])

        logger.info(
            f"Selected {len(selected)} clips from {len(segments)} segments "
            f"(threshold={score_threshold}, max={max_clips}, mode={clip_mode})"
        )

        return selected

    def generate_clips(
        self,
        video_path: str,
        clips_metadata: List[Dict[str, Any]],
        output_dir: str,
        clip_mode: str = "short",
    ) -> List[Dict[str, Any]]:
        """
        Generate video clip files using FFmpeg.
        Duration limits are driven by the clip_mode profile.
        """
        profile = get_mode_profile(clip_mode)
        os.makedirs(output_dir, exist_ok=True)
        generated = []

        # Get total video duration for bounds checking
        total_duration = video_service.get_video_duration(video_path)

        for i, clip_meta in enumerate(clips_metadata):
            start = max(0, clip_meta["start"])
            end = clip_meta["end"]

            # Enforce minimum clip duration from profile
            if end - start < profile["min_clip"]:
                end = start + profile["min_clip"]

            # Enforce maximum clip duration from profile
            if end - start > profile["max_clip"]:
                end = start + profile["max_clip"]

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
                    f"{output_filename} ({start:.1f}s–{end:.1f}s, "
                    f"score={clip_meta.get('score', 0)}, mode={clip_mode})"
                )

            except Exception as e:
                logger.error(f"Failed to generate clip {clip_id}: {e}")
                continue

        return generated


# Module-level singleton
clip_engine = ClipEngine()
