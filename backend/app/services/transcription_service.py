"""Transcription service — Whisper-based audio transcription with scene-aware splitting."""
import logging
import os
from typing import List, Dict, Any, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)
# ═══════════════════════════════════════════════════════════════════════════
# MONKEYPATCH: Fix GPT2Tokenizer attribute error in certain transformers versions
# ═══════════════════════════════════════════════════════════════════════════
try:
    from transformers import GPT2Tokenizer
    if not hasattr(GPT2Tokenizer, "additional_special_tokens"):
        logger.info("Monkeypatching GPT2Tokenizer.additional_special_tokens")
        GPT2Tokenizer.additional_special_tokens = []
except ImportError:
    pass
# ═══════════════════════════════════════════════════════════════════════════


class TranscriptionService:
    """Lazy-loaded Whisper transcription with configurable model size."""

    def __init__(self, model_name: str = None):
        self._model_name = model_name or settings.WHISPER_MODEL
        self._model = None

    def _load_model(self):
        """Lazy-load the Whisper model on first use."""
        if self._model is None:
            import whisper
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Whisper model '{self._model_name}' on {device}")
            self._model = whisper.load_model(self._model_name, device=device)
            logger.info("Whisper model loaded successfully")
        return self._model

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe audio file and return raw Whisper segments.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        logger.info(f"Transcribing: {audio_path}")

        import torch
        use_fp16 = torch.cuda.is_available()
        result = model.transcribe(audio_path, verbose=False, fp16=use_fp16)
        raw_segments = result.get("segments", [])

        logger.info(f"Transcription complete: {len(raw_segments)} raw segments")
        return raw_segments

    def align_segments_to_scenes(
        self, 
        raw_segments: List[Dict[str, Any]], 
        scenes: List[Tuple[float, float]],
        target_duration: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Align transcription segments to visual scene boundaries.
        Groups Whisper segments that fall within the same scene.
        """
        if not scenes:
            logger.warning("No scenes provided for alignment, falling back to time-based split.")
            return self._time_based_split(raw_segments, target_duration)

        aligned = []
        current_scene_idx = 0
        
        # Start with the first scene
        current_chunk = {
            "start": scenes[0][0],
            "end": scenes[0][1],
            "text": ""
        }

        for seg in raw_segments:
            seg_center = (seg["start"] + seg["end"]) / 2
            
            # Find which scene this segment belongs to
            while current_scene_idx < len(scenes) and seg_center > scenes[current_scene_idx][1]:
                # Move to next scene
                if current_chunk["text"].strip():
                    aligned.append(current_chunk)
                
                current_scene_idx += 1
                if current_scene_idx < len(scenes):
                    current_chunk = {
                        "start": scenes[current_scene_idx][0],
                        "end": scenes[current_scene_idx][1],
                        "text": ""
                    }
                else:
                    break
            
            if current_scene_idx < len(scenes):
                current_chunk["text"] += " " + seg["text"].strip()
            else:
                # Segment falls after last detected scene
                pass

        if current_chunk["text"].strip():
            aligned.append(current_chunk)

        logger.info(f"Aligned {len(raw_segments)} segments into {len(aligned)} scene-aware chunks")
        return aligned

    def _time_based_split(self, raw_segments: List[Dict[str, Any]], target_duration: float) -> List[Dict[str, Any]]:
        """Fallback simple time-based splitting."""
        if not raw_segments: return []
        merged = []
        current = {"start": raw_segments[0]["start"], "end": raw_segments[0]["end"], "text": raw_segments[0]["text"].strip()}
        for seg in raw_segments[1:]:
            if seg["end"] - current["start"] <= target_duration:
                current["end"] = seg["end"]
                current["text"] += " " + seg["text"].strip()
            else:
                merged.append(current)
                current = {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
        if current["text"].strip(): merged.append(current)
        return merged

    def transcribe_and_split(self, audio_path: str, target_duration: float = None) -> List[Dict[str, Any]]:
        raw = self.transcribe(audio_path)
        return self._time_based_split(raw, target_duration or settings.TARGET_SEGMENT_DURATION)


# Module-level singleton
transcription_service = TranscriptionService()
