"""Video service — FFmpeg-based audio extraction, scene detection, and vertical rendering."""
import logging
import os
import subprocess
import tempfile
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoService:
    """Handles FFmpeg operations for audio extraction and vertical social media rendering."""

    @staticmethod
    def extract_audio(video_path: str, output_audio_path: str) -> str:
        os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
        
        cmd = [
            ffmpeg_bin, "-y",
            "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
            output_audio_path,
        ]

        logger.info(f"Extracting audio: {video_path} → {output_audio_path}")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return output_audio_path

    @staticmethod
    def get_video_duration(video_path: str) -> float:
        ffprobe_bin = getattr(settings, "FFPROBE_PATH", "ffprobe")
        cmd = [
            ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path,
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return float(result.stdout.decode().strip())
        except:
            return 0.0

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        ffprobe_bin = getattr(settings, "FFPROBE_PATH", "ffprobe")
        cmd = [
            ffprobe_bin, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-show_entries", "format=duration,size", "-of", "json", video_path,
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            import json
            probe = json.loads(result.stdout.decode())
            stream = probe.get("streams", [{}])[0]
            fmt = probe.get("format", {})
            return {
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
                "duration": float(fmt.get("duration", 0)),
            }
        except:
            return None

    @staticmethod
    def create_vertical_clip(
        video_path: str, 
        start: float, 
        end: float, 
        output_path: str, 
        transcript_segments: List[Dict[str, Any]] = None
    ) -> str:
        """
        Creates a vertical 9:16 clip with center-cropping and burned-in subtitles.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
        info = VideoService.get_video_info(video_path)
        
        if not info:
            raise RuntimeError("Could not retrieve video info for rendering.")

        # 1. Calculate 9:16 crop (center-weighted)
        target_aspect = 9 / 16
        current_w, current_h = info["width"], info["height"]
        
        # We assume height is the limiting factor (standard landscape)
        new_w = int(current_h * target_aspect)
        offset_x = (current_w - new_w) // 2
        
        crop_filter = f"crop={new_w}:{current_h}:{offset_x}:0,scale=1080:1920"

        # 2. Subtitles logic
        filters = [crop_filter]
        srt_temp = None
        
        if transcript_segments:
            # Create a temporary .srt file
            srt_temp = VideoService._create_temp_srt(transcript_segments, start)
            # FFmpeg's subtitles filter requires a specific path format on Windows
            srt_path_fixed = srt_temp.replace("\\", "/").replace(":", "\\:")
            filters.append(f"subtitles='{srt_path_fixed}':force_style='FontSize=24,PrimaryColour=&H00FFFF,Alignment=10'")

        filter_str = ",".join(filters)

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(end - start),
            "-vf", filter_str,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        logger.info(f"Rendering vertical clip: {output_path}")
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path
        finally:
            if srt_temp and os.path.exists(srt_temp):
                try: os.remove(srt_temp)
                except: pass

    @staticmethod
    def _create_temp_srt(segments: List[Dict[str, Any]], global_offset: float) -> str:
        """Generates a temporary .srt file from segments."""
        fd, path = tempfile.mkstemp(suffix=".srt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments):
                # Calculate relative timestamps for the clip
                s = max(0, seg["start"] - global_offset)
                e = max(0, seg["end"] - global_offset)
                
                def format_time(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    sec = int(seconds % 60)
                    ms = int((seconds % 1) * 1000)
                    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

                f.write(f"{i+1}\n")
                f.write(f"{format_time(s)} --> {format_time(e)}\n")
                f.write(f"{seg['text'].strip()}\n\n")
        return path


video_service = VideoService()
