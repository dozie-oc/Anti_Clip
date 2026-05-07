"""AntiClip API — FastAPI application entry point."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import process, projects, upload
from app.database import engine, Base
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Ensure storage directories
    for d in [settings.UPLOAD_DIR, settings.CLIPS_DIR, settings.TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
    logger.info("Storage directories ready")

    # Log LLM status
    if settings.OPENAI_API_KEY:
        logger.info(f"LLM: OpenAI ({settings.LLM_MODEL_NAME})")
    else:
        logger.info("LLM: Fallback heuristic mode (set OPENAI_API_KEY for AI scoring)")

    yield


app = FastAPI(
    title="AntiClip API",
    description="AI Video Clipper — local-first processing pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for serving generated clips
os.makedirs("storage/clips", exist_ok=True)
app.mount("/clips", StaticFiles(directory="storage/clips"), name="clips")

# Also serve uploaded files for preview
os.makedirs("storage/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="storage/uploads"), name="uploads")

# API routes
PREFIX = "/api/v1"
app.include_router(upload.router, prefix=PREFIX, tags=["Upload"])
app.include_router(projects.router, prefix=PREFIX, tags=["Projects"])
app.include_router(process.router, prefix=PREFIX, tags=["Process"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    from app.models.schemas import HealthResponse
    return HealthResponse(
        status="ok",
        whisper_model=settings.WHISPER_MODEL,
        llm_model=settings.LLM_MODEL_NAME,
        llm_configured=bool(settings.OPENAI_API_KEY),
    )
