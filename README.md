# Heirloom
By Khush Mehta and Ethan Olchik

## Overview
Heirloom is a full-stack web application that lets families preserve multimedia memories (photos, letters, audio, and video), extract structured memory units using Gemini, and then ask questions answered with grounded responses and personal voice synthesis via ElevenLabs. The system is designed to feel like a living archive: upload artifacts, let the backend extract structured memories, then ask questions and hear replies spoken aloud in the voice of the person it is describing.

## Repo Structure
- `backend/`: FastAPI service for uploads, memory extraction, retrieval, and voice responses.
- `frontend/`: Next.js app for the "Preserve" and "Discover" experiences.
- `docs/`: Architecture and operational notes.

## Local Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ (or 20+)
- An S3-compatible bucket (AWS S3, MinIO, etc.)
- A Supabase project with tables: `profiles`, `media_assets`, `jobs`, `memory_units`
- API keys for Google Gemini and ElevenLabs

### Environment Variables
Create a `.env` file in the repo root (use `.env.example` as a template):
```
# AWS / S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
AWS_S3_BUCKET=...
AWS_S3_ENDPOINT_URL=...   # optional for non-AWS S3

# Supabase
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

# Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-pro

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...   # optional; can be created via /profiles/voice-clone

# Optional
DEFAULT_TOP_K=8
LOG_LEVEL=INFO
CORS_ALLOW_ORIGINS=http://localhost:3000
```

For the frontend, set a `.env.local` in `frontend/` with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend Setup
```
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Setup
```
cd frontend
npm install
npm run dev
```

Then visit:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## API Overview
Base path: `/api/v1`

**Profiles & Media**
- `POST /profiles` — create a profile
- `POST /media-assets/upload-init` — request a presigned upload URL
- `POST /media-assets/upload-confirm` — confirm upload + queue extraction
- `GET /profiles/{profile_id}/media-assets` — list media assets
- `GET /media-assets/{media_asset_id}/memory-units` — list extracted memory units
- `PATCH /media-assets/{media_asset_id}/memory-units` — update extracted metadata

**Q&A**
- `POST /profiles/{profile_id}/ask` — return text answer with source URLs
- `POST /profiles/{profile_id}/ask-voice` — return text + audio response

**Voice**
- `POST /profiles/voice-clone` — clone voice from an audio sample

**Worker**
- `GET /api/v1/worker/status` — worker health
- `POST /api/v1/worker/start` — start extraction worker
- `POST /api/v1/worker/stop` — stop extraction worker
