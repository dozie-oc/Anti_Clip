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
    DB_FILE: str = "storage/projects.json"

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 2048
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mkv", ".mov", ".avi", ".webm"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
