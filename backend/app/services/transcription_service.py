"""Transcription service — Whisper-based audio transcription with segment splitting."""
import logging
import os
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


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
        Each segment: {start, end, text, ...}
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        logger.info(f"Transcribing: {audio_path}")

        result = model.transcribe(audio_path, verbose=False)
        raw_segments = result.get("segments", [])

        logger.info(f"Transcription complete: {len(raw_segments)} raw segments")
        return raw_segments

    def transcribe_and_split(
        self,
        audio_path: str,
        target_duration: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Transcribe and merge/split segments into chunks of ~target_duration seconds.
        Returns clean segments: [{start, end, text}, ...]
        """
        target_duration = target_duration or settings.TARGET_SEGMENT_DURATION
        raw_segments = self.transcribe(audio_path)

        if not raw_segments:
            return []

        # Merge small Whisper segments into target-duration chunks
        merged = []
        current = {
            "start": raw_segments[0]["start"],
            "end": raw_segments[0]["end"],
            "text": raw_segments[0]["text"].strip(),
        }

        for seg in raw_segments[1:]:
            seg_duration = seg["end"] - current["start"]

            if seg_duration <= target_duration:
                # Extend current chunk
                current["end"] = seg["end"]
                current["text"] += " " + seg["text"].strip()
            else:
                # Save current and start new chunk
                merged.append(current)
                current = {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                }

        # Don't forget the last chunk
        if current["text"].strip():
            merged.append(current)

        logger.info(
            f"Merged {len(raw_segments)} raw segments → "
            f"{len(merged)} chunks (~{target_duration}s each)"
        )
        return merged


# Module-level singleton (lazy — won't load model until first call)
transcription_service = TranscriptionService()
