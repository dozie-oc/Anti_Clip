from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.routes import process, projects, upload
from app.database import engine, Base
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Ensure storage directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CLIPS_DIR, exist_ok=True)
    os.makedirs(os.path.join("storage", "temp"), exist_ok=True)
    
    yield

app = FastAPI(
    title="AntiClip API",
    description="AI Video Clipper — REST backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev, allow all or specify
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for serving clips
app.mount("/clips", StaticFiles(directory="storage/clips"), name="clips")

# Routers
PREFIX = "/api/v1"
app.include_router(upload.router,   prefix=PREFIX, tags=["Upload"])
app.include_router(projects.router, prefix=PREFIX, tags=["Projects"])
app.include_router(process.router,  prefix=PREFIX, tags=["Process"])

@app.get("/health")
async def health():
    return {"status": "ok"}
