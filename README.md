# AntiClip — AI Video Clipper

**Local-first AI-powered video clipping platform.**  
Upload long-form videos, describe what clips you want, and let AI do the rest.

---

## Architecture

```
Frontend (React + Vite + TailwindCSS)
        ↓ Axios
FastAPI REST API
        ↓
Background Worker Thread
        ↓
┌──────────────────────────────┐
│  1. FFmpeg Audio Extraction  │
│  2. Whisper Transcription    │
│  3. LLM Segment Scoring     │
│  4. FFmpeg Clip Generation   │
└──────────────────────────────┘
        ↓
Results Dashboard (video players + downloads)
```

## Tech Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Frontend    | React 18, Vite, TailwindCSS, Zustand, Axios  |
| Backend     | FastAPI, SQLAlchemy, SQLite                   |
| AI          | OpenAI Whisper (transcription), GPT-4o (scoring) |
| Video       | FFmpeg (audio extraction + clip cutting)      |

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **FFmpeg** (must be in your system PATH)
- **OpenAI API key** (optional — falls back to heuristic scoring)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and set your OPENAI_API_KEY

# Start server
uvicorn app.main:app --reload
```

The API will be running at `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The UI will be at `http://localhost:5173`

## Configuration

Edit `backend/.env`:

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional
LLM_MODEL_NAME=gpt-4o          # or gpt-4.1, gpt-4o-mini
WHISPER_MODEL=base              # tiny, base, small, medium, large
LLM_SCORE_THRESHOLD=6           # minimum score (1-10) to select a clip
LLM_MAX_CLIPS=10                # max clips per project
```

> **No API key?** The system works without one — it uses heuristic-based scoring
> (text length, keyword matching, emotional markers) as a fallback.

## How It Works

1. **Upload** a video (MP4, MKV, MOV, AVI, WebM)
2. **Write a prompt** describing the clips you want:
   - *"Find funny moments"*
   - *"Create viral YouTube Shorts"*
   - *"Extract emotional dialogue"*
3. **Start processing** — the pipeline runs in the background:
   - Audio extraction via FFmpeg
   - Speech-to-text via Whisper
   - AI scoring of transcript segments
   - Clip generation via FFmpeg
4. **Download clips** with embedded video players and score badges

## API Endpoints

| Method   | Endpoint                          | Description                    |
|----------|-----------------------------------|--------------------------------|
| `POST`   | `/api/v1/upload`                  | Upload video + create project  |
| `GET`    | `/api/v1/projects`                | List all projects              |
| `GET`    | `/api/v1/projects/{id}`           | Get project details            |
| `PATCH`  | `/api/v1/projects/{id}`           | Update prompt/name             |
| `DELETE` | `/api/v1/projects/{id}`           | Delete project + files         |
| `POST`   | `/api/v1/projects/{id}/process`   | Start AI pipeline              |
| `POST`   | `/api/v1/projects/{id}/reset`     | Reset for reprocessing         |
| `GET`    | `/api/v1/projects/{id}/job`       | Get job/pipeline status        |
| `GET`    | `/health`                         | System health check            |

## Project Structure

```
Anti_Clip/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifecycle
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── worker.py            # Background processing pipeline
│   │   ├── core/
│   │   │   └── config.py        # Settings (env-driven)
│   │   ├── models/
│   │   │   ├── project.py       # Project ORM model
│   │   │   ├── job.py           # Job ORM model
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── api/routes/
│   │   │   ├── upload.py        # POST /upload
│   │   │   ├── projects.py      # CRUD /projects
│   │   │   └── process.py       # POST /process
│   │   └── services/
│   │       ├── llm_service.py   # OpenAI + fallback adapter
│   │       ├── transcription_service.py  # Whisper
│   │       ├── clip_engine.py   # LLM scoring + clip generation
│   │       └── video_service.py # FFmpeg operations
│   ├── storage/                 # Auto-created at runtime
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── UploadPage.jsx
    │   │   ├── ProjectsPage.jsx
    │   │   ├── ProjectDetailPage.jsx
    │   │   ├── QueuePage.jsx
    │   │   └── SettingsPage.jsx
    │   ├── components/layout/
    │   ├── services/api.js
    │   └── store/appStore.js
    ├── package.json
    └── tailwind.config.js
```

## LLM Architecture

The system uses an **adapter pattern** for LLM providers:

```
LLMProvider (abstract)
  ├── OpenAIProvider    ← primary (GPT-4o)
  └── FallbackProvider  ← heuristic scoring (no API key needed)
```

Future providers (Ollama, Llama, Mistral) can be added by implementing
the `LLMProvider` interface in `services/llm_service.py`.
