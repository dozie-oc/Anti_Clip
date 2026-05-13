# AntiClip — Local-First AI Video Clipper

AntiClip is a powerful, fully local AI pipeline for video processing, designed to help you create viral social media content and condensed video recaps without high API costs.

## 🚀 Key Features

### 🎬 Viral Clips Mode (Phase 1)
- **Scene-Aware Cuts:** Uses `PySceneDetect` to ensure clips start and end on natural visual boundaries.
- **Vertical Rendering:** Automatic center-cropping to 9:16 aspect ratio for TikTok, Shorts, and Reels.
- **Burned-in Subtitles:** High-visibility captions hard-coded into the video.
- **Local LLM Analysis:** Integrated with **Ollama (qwen2.5-coder:7b)** for structured viral scoring (`hook_strength`, `emotional_intensity`).

### 🎙️ Narration Summary Mode (Phase 2)
- **AI Recap Generation:** Condensed summaries for long-form content (movies, episodes, tutorials).
- **Local TTS:** Uses **Piper TTS (lessac-medium)** for high-quality, professional narration.
- **Intelligent Scripting:** AI generates a script and automatically identifies which scenes to show during the recap.

## 🛠️ Setup

1. **Ollama:** Install [Ollama](https://ollama.com/) and run:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
2. **FFmpeg:** Ensure `ffmpeg` and `ffprobe` are in your system PATH.
3. **Piper Models:** Place `.onnx` and `.onnx.json` voice models in `storage/models/piper/`.
4. **Environment:** Copy `.env.example` to `.env` and configure your paths.

## ⚙️ Running Locally

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

