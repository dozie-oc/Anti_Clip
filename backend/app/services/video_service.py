"""Video service — FFmpeg-based audio extraction and video info."""
import logging
import os
import subprocess

from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoService:
    """Handles FFmpeg operations for audio extraction and video metadata."""

    @staticmethod
    def extract_audio(video_path: str, output_audio_path: str) -> str:
        """
        Extract audio from video using FFmpeg subprocess.
        Outputs 16kHz mono WAV (optimal for Whisper).
        """
        os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)
        ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
        logger.info(f"Using FFmpeg binary at: {ffmpeg_bin}")

        cmd = [
            ffmpeg_bin, "-y",
            "-i", video_path,
            "-vn",                    # no video
            "-acodec", "pcm_s16le",   # 16-bit PCM
            "-ac", "1",               # mono
            "-ar", "16000",           # 16kHz sample rate
            output_audio_path,
        ]

        logger.info(f"Extracting audio: {video_path} → {output_audio_path}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=600,  # 10 minute timeout
            )
            logger.info("Audio extraction complete")
            return output_audio_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and add it to your PATH."
            )

    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        ffprobe_bin = getattr(settings, "FFPROBE_PATH", "ffprobe")
        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True, timeout=30,
            )
            return float(result.stdout.decode().strip())
        except Exception as e:
            logger.warning(f"Could not get video duration: {e}")
            return 0.0

    @staticmethod
    def cut_clip(
        video_path: str,
        start: float,
        end: float,
        output_path: str,
    ) -> str:
        """
        Cut a clip from a video using FFmpeg.
        Uses stream copy for speed when possible.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        duration = end - start
        ffmpeg_bin = os.path.normpath(getattr(settings, "FFMPEG_PATH", "ffmpeg"))

        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-movflags", "+faststart",
            output_path,
        ]

        logger.info(f"Cutting clip: {start:.1f}s – {end:.1f}s → {output_path}")
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=300,
            )
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg clip error: {e.stderr.decode()}")
            raise RuntimeError(f"Clip generation failed: {e.stderr.decode()}")

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """Get video metadata using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-show_entries", "format=duration,size",
            "-of", "json",
            video_path,
        ]
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True, timeout=30,
            )
            import json
            probe = json.loads(result.stdout.decode())
            stream = probe.get("streams", [{}])[0]
            fmt = probe.get("format", {})
            return {
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
                "duration": float(fmt.get("duration", 0)),
                "codec": stream.get("codec_name", "unknown"),
            }
        except Exception as e:
            logger.warning(f"Could not get video info: {e}")
            return None


video_service = VideoService()
