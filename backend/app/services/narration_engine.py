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
        
        # 3. Parse [SCENE] markers and assemble video
        markers = self._parse_markers(script)
        
        # Fallback: if no markers found, use first 30 seconds
        if not markers:
            markers = [{"start": 0, "end": 30}]

        final_video_path = os.path.join(output_dir, "narration_summary.mp4")
        
        try:
            self._assemble_final_video(video_path, markers, tts_path, final_video_path)
            logger.info(f"Narration video assembled at {final_video_path}")
            status = "completed"
        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            status = "failed_render"

        return [{
            "id": "summary_01",
            "filename": "narration_summary.mp4",
            "script": script,
            "tts_path": tts_path,
            "status": status
        }]

    def _parse_markers(self, script: str) -> List[Dict[str, float]]:
        """Extracts [SCENE: start - end] markers from the script."""
        markers = []
        # Support both [SCENE: 10 - 20] and [SCENE: 10.5-20.5]
        pattern = r"\[SCENE:\s*([\d\.]+)\s*-\s*([\d\.]+)\]"
        matches = re.finditer(pattern, script)
        for match in matches:
            markers.append({
                "start": float(match.group(1)),
                "end": float(match.group(2))
            })
        return markers

    def _assemble_final_video(self, video_path: str, markers: List[Dict], tts_path: str, output_path: str):
        """Uses FFmpeg to stitch scenes and overlay narration."""
        import subprocess
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
        
        # 1. Create a filter_complex to stitch video segments
        # This is a simplified version: we'll take the segments and concat them
        inputs = []
        filter_parts = []
        
        for i, m in enumerate(markers[:10]): # Limit to 10 scenes for stability
            inputs.extend(["-ss", str(m["start"]), "-t", str(m["end"] - m["start"]), "-i", video_path])
            filter_parts.append(f"[{i}:v][{i}:a]")
        
        # Add TTS as the last input
        inputs.extend(["-i", tts_path])
        tts_idx = len(markers[:10])
        
        # Concat video parts and mix with TTS
        # [0:v][0:a][1:v][1:a]... concat=n=N:v=1:a=1 [v][a]
        n = len(markers[:10])
        filter_complex = f"{''.join(filter_parts)}concat=n={n}:v=1:a=1[v_raw][a_raw];"
        # Mix tts audio over concatenated audio
        filter_complex += f"[a_raw][{tts_idx}:a]amix=inputs=2:duration=first[a]"
        
        cmd = [
            ffmpeg_bin, "-y"
        ] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[v_raw]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]
        
        logger.info(f"Assembling narration video with {n} scenes...")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


narration_engine = NarrationEngine()
