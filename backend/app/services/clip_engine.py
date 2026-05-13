"""
Clip engine — orchestrates LLM scoring, ranking, and vertical FFmpeg generation.
"""
import logging
import os
import uuid
from typing import List, Dict, Any

from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.video_service import video_service

logger = logging.getLogger(__name__)

# Mode profiles for duration and thresholds
MODE_PROFILES = {
    "short": {
        "min_clip": 15.0,
        "max_clip": 60.0,
        "score_threshold": 6,
        "max_clips": 10,
    },
    "long": {
        "min_clip": 60.0,
        "max_clip": 300.0,
        "score_threshold": 5,
        "max_clips": 5,
    },
}

class ClipEngine:
    """Scores, ranks, and generates professional social media clips."""

    def select_clips(self, segments: List[Dict[str, Any]], user_prompt: str, clip_mode: str = "short") -> List[Dict[str, Any]]:
        profile = MODE_PROFILES.get(clip_mode, MODE_PROFILES["short"])
        
        # 1. Get detailed scores from LLM
        scored_data = llm_service.score_segments_batched(segments, user_prompt, clip_mode=clip_mode)
        score_map = {s["index"]: s for s in scored_data}

        candidates = []
        for i, seg in enumerate(segments):
            metrics = score_map.get(i, {"score": 5, "hook_strength": 5, "emotional_intensity": 5, "engagement_reason": "N/A"})
            
            # Better ranking: weight score and hook strength
            # (score * 0.5) + (hook * 0.3) + (intensity * 0.2)
            rank_score = (metrics["score"] * 0.5) + (metrics.get("hook_strength", 5) * 0.3) + (metrics.get("emotional_intensity", 5) * 0.2)

            if metrics["score"] >= profile["score_threshold"]:
                candidates.append({
                    "id": str(uuid.uuid4()),
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "score": metrics["score"],
                    "rank_score": rank_score,
                    "metrics": metrics,
                })

        # 2. Sort by rank_score and take top N
        candidates.sort(key=lambda x: x["rank_score"], reverse=True)
        selected = candidates[:profile["max_clips"]]
        selected.sort(key=lambda x: x["start"])  # Return in timeline order

        return selected

    def generate_clips(
        self, 
        video_path: str, 
        clips_metadata: List[Dict[str, Any]], 
        output_dir: str, 
        clip_mode: str = "short"
    ) -> List[Dict[str, Any]]:
        """Generates vertical clips with burned-in subtitles."""
        os.makedirs(output_dir, exist_ok=True)
        generated = []
        
        # We need the full transcript (from project context) to burn subs accurately
        # clips_metadata contains the selected segments
        
        for i, clip_meta in enumerate(clips_metadata):
            start, end = clip_meta["start"], clip_meta["end"]
            clip_id = clip_meta["id"]
            filename = f"clip_{i+1:02d}_{clip_id[:8]}.mp4"
            output_path = os.path.join(output_dir, filename)

            try:
                # In scene-aware mode, a 'clip' is usually one or more scenes
                # For now, we pass the single segment's text for subtitling
                # In a more advanced version, we'd pass all segments falling in [start, end]
                subs = [{"start": start, "end": end, "text": clip_meta["text"]}]

                video_service.create_vertical_clip(
                    video_path, start, end, output_path, transcript_segments=subs
                )

                generated.append({
                    "id": clip_id,
                    "filename": filename,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(end - start, 2),
                    "text": clip_meta["text"],
                    "score": clip_meta["score"],
                    "metrics": clip_meta["metrics"]
                })
            except Exception as e:
                logger.error(f"Failed to generate clip {i+1}: {e}")

        return generated

clip_engine = ClipEngine()
