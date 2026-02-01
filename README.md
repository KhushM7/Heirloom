# Heirloom
By Khush Mehta and Ethan Olchik
## Overview
Heirloom is a full‑stack web application that lets families preserve multimedia memories (photos, letters, audio, and video), extract structured “memory units” from those artifacts using Gemini, and then ask questions that are answered with grounded responses and personal voice synthesis via ElevenLabs. The system is designed to feel like a living archive: upload artifacts, let the backend extract structured memories, then ask questions and hear replies spoken aloud in the voice of the person it is describing.

This repository contains:
- **Backend**: FastAPI service for uploads, memory extraction, retrieval, and voice responses. (`/app`)
- **Frontend**: Next.js app for the “Preserve (Upload content)” and “Discover (Interact with the content)” experiences. (`/frontend`)

## Key Features
- **Upload workflow with S3 presigned URLs** for safe, direct-to-storage uploads.
- **Memory extraction worker** that processes queued jobs and writes memory units to Supabase.
- **Question answering** over extracted memories using Gemini context packing.
- **Voice clone & TTS** through ElevenLabs to clone a personal voice from an uploaded audio clip as well as speak answers.
- **Source citations** for answers by linking back to uploaded media assets.

## How It Works
### 1) Create a profile
The frontend creates a profile with a date of birth and voice sample. The backend stores the profile in Supabase.

### 2) Upload media assets
Uploads are handled in two phases:
1. **Upload init**: the backend validates file size/type and returns a presigned URL and object key.
2. **Upload confirm**: after the client uploads to S3, the backend confirms the object, creates a `media_assets` row, and queues an extraction job in `jobs`.

### 3) Extract memory units
A background **ExtractionWorker** polls queued jobs, downloads the media, and asks Gemini to extract a single structured memory unit per asset. It writes the extracted data into Supabase `memory_units`.

### 4) Ask questions
The QA endpoint:
- Extracts keywords from the user question using Gemini to group keywords and get similar as well as exact matching tags.
- Queries Supabase for relevant memory units.
- Builds a context pack and asks Gemini to answer **only from that context**.

### 5) Speak the answer
Using the voice ID exists from ElevenLabs instant voice cloning the answer is turned into audio and returned to the frontend as base64.

## Architecture
```
Frontend (Next.js) ───────────────┐
                                 │
                                 ▼
                           FastAPI Backend
                                 │
                                 ├─ S3-compatible storage (uploads)
                                 ├─ Supabase (profiles, assets, jobs, memory_units)
                                 ├─ Gemini (memory extraction + QA)
                                 └─ ElevenLabs (voice clone + TTS)
```

## Project Structure
```
app/                      FastAPI backend
  api/                    API routes + schemas
  core/                   settings, S3 + Supabase helpers, worker
  db/                     Supabase client + retrieval queries
  llm/                    Gemini client + prompts
  retrieval/              keyword extraction + context building
  storage/                streaming + URL resolution helpers
  elevenLabs/             voice cloning + TTS helpers
frontend/                 Next.js frontend
  app/                    App Router pages (home, preserve, discover)
  components/             UI components
  lib/                    API client + profile state
```

## Supported Media Types
The backend accepts uploads up to **100 MB** in the following formats:
- Video: `.mp4`, `.mov`
- Audio: `.mp3`, `.wav`
- Images: `.png`, `.jpg`, `.jpeg`
- Text: `.txt`

## Local Development

### Prerequisites
- **Python 3.14+**
- **Node.js 18+** (or 20+)
- An **S3-compatible bucket** (AWS S3, MinIO, etc.)
- A **Supabase** project with tables: `profiles`, `media_assets`, `jobs`, `memory_units`
- API keys for **Google Gemini** and **ElevenLabs**

### Environment Variables
Create a `.env` file in the repo root (used by the backend) with:
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
```

For the frontend, set a `.env.local` in `frontend/` with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend Setup
```
cd frontend
npm install
npm run dev
```

Then visit:
- Frontend: http://localhost:3000

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

## Storage & Data Model (High-Level)
- `profiles`: person metadata (name, DOB, voice_id)
- `media_assets`: uploaded artifacts (file name, mime, bytes)
- `jobs`: extraction queue entries
- `memory_units`: extracted structured memories
