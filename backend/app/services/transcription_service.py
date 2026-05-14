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
        """Lazy-load the Faster-Whisper model on first use."""
        if self._model is None:
            from faster_whisper import WhisperModel
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Use int8 for CPU, float16 or int8_float16 for CUDA
            compute_type = "int8" if device == "cpu" else "float16"
            
            logger.info(f"Loading Faster-Whisper model '{self._model_name}' on {device} ({compute_type})")
            self._model = WhisperModel(self._model_name, device=device, compute_type=compute_type)
            logger.info("Faster-Whisper model loaded successfully")
        return self._model

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Transcribe audio file using faster-whisper and return segments as dicts.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()
        logger.info(f"Transcribing (faster-whisper): {audio_path}")

        # beam_size=5 and vad_filter=True for better quality and noise handling
        segments_iter, info = model.transcribe(
            audio_path, 
            beam_size=5, 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Convert iterator to list of dicts for compatibility
        raw_segments = []
        for s in segments_iter:
            raw_segments.append({
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "avg_logprob": s.avg_logprob
            })

        logger.info(f"Transcription complete: {len(raw_segments)} segments (lang={info.language})")
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
            "text": "",
            "logprobs": []
        }

        for seg in raw_segments:
            seg_center = (seg["start"] + seg["end"]) / 2
            
            # Find which scene this segment belongs to
            while current_scene_idx < len(scenes) and seg_center > scenes[current_scene_idx][1]:
                # Move to next scene
                if current_chunk["text"].strip():
                    # Calculate final avg logprob
                    if current_chunk["logprobs"]:
                        current_chunk["avg_logprob"] = sum(current_chunk["logprobs"]) / len(current_chunk["logprobs"])
                    else:
                        current_chunk["avg_logprob"] = -1.0
                    del current_chunk["logprobs"]
                    aligned.append(current_chunk)
                
                current_scene_idx += 1
                if current_scene_idx < len(scenes):
                    current_chunk = {
                        "start": scenes[current_scene_idx][0],
                        "end": scenes[current_scene_idx][1],
                        "text": "",
                        "logprobs": []
                    }
                else:
                    break
            
            if current_scene_idx < len(scenes):
                current_chunk["text"] += " " + seg["text"].strip()
                if "avg_logprob" in seg:
                    current_chunk["logprobs"].append(seg["avg_logprob"])
            else:
                # Segment falls after last detected scene
                pass

        if current_chunk["text"].strip():
            if current_chunk["logprobs"]:
                current_chunk["avg_logprob"] = sum(current_chunk["logprobs"]) / len(current_chunk["logprobs"])
            else:
                current_chunk["avg_logprob"] = -1.0
            del current_chunk["logprobs"]
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
