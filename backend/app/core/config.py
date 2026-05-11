"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "AntiClip"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Storage paths (relative to backend/)
    UPLOAD_DIR: str = "storage/uploads"
    CLIPS_DIR: str = "storage/clips"
    TEMP_DIR: str = "storage/temp"

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 2048
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mkv", ".mov", ".avi", ".webm"]

    # ── LLM Configuration ──────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4o"
    LLM_MAX_SEGMENTS_PER_BATCH: int = 20
    LLM_SCORE_THRESHOLD: int = 6  # minimum score to select a segment
    LLM_MAX_CLIPS: int = 10

    # ── Ollama Configuration ──────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_CPU_ONLY: bool = False   # set True to force CPU-only inference
    OLLAMA_TIMEOUT: int = 120       # seconds per batch request

    # ── Video / Audio processing ──────────────────────────────────────────
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large

    # ── Clip defaults ──────────────────────────────────────────────────────
    MIN_CLIP_DURATION: float = 5.0
    MAX_CLIP_DURATION: float = 60.0
    TARGET_SEGMENT_DURATION: float = 15.0  # target seconds per transcript segment

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
