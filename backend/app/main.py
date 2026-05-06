"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.routes import process, projects, upload
from app.core.config import settings
from app.core.storage import ensure_storage_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup/shutdown logic."""
    ensure_storage_dirs()
    yield


app = FastAPI(
    title="AntiClip API",
    description="AI Video Clipper — REST backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(upload.router,   prefix=PREFIX, tags=["Upload"])
app.include_router(projects.router, prefix=PREFIX, tags=["Projects"])
app.include_router(process.router,  prefix=PREFIX, tags=["Process"])


# ── Health ────────────────────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}
