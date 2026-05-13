"""
Narration Engine — orchestrates narration script generation, TTS, and video assembly.
"""
import logging
import os
import re
from typing import List, Dict, Any

from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.video_service import video_service

logger = logging.getLogger(__name__)

class NarrationEngine:
    """Handles the full narration summary pipeline."""

    def process_narration_mode(
        self, 
        project_id: str, 
        full_transcript: str, 
        target_minutes: int, 
        video_path: str,
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Executes the narration summary pipeline:
        1. Generate Script -> 2. Generate TTS -> 3. Assemble Video
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Generate Script via LLM
        logger.info(f"Generating narration script for {project_id}...")
        script = llm_service.generate_narration_script(full_transcript, target_minutes)
        
        # 2. Generate TTS Audio
        tts_path = os.path.join(output_dir, "narration_voice.wav")
        tts_service.generate_speech(script, tts_path)
        
        # 3. Parse [SCENE] markers and assemble
        # This is where we'd use FFmpeg complex filters to mix audio and stitch video.
        # For the MVP, we'll return the script and audio path.
        
        logger.info(f"Narration pipeline complete for {project_id}")
        
        return [{
            "id": "summary_01",
            "filename": "narration_summary.mp4",
            "script": script,
            "tts_path": tts_path,
            "status": "ready_to_render" # Full rendering logic to be added
        }]

    def _parse_markers(self, script: str) -> List[Dict[str, float]]:
        """Extracts [SCENE: start - end] markers from the script."""
        markers = []
        pattern = r"\[SCENE:\s*([\d\.]+)\s*-\s*([\d\.]+)\]"
        matches = re.finditer(pattern, script)
        for match in matches:
            markers.append({
                "start": float(match.group(1)),
                "end": float(match.group(2))
            })
        return markers

narration_engine = NarrationEngine()
