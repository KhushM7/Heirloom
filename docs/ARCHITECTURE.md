# Architecture Layout
```
/backend
  /app
    /api
    /core
    /db
    /elevenLabs
    /llm
    /retrieval
    /storage
  requirements.txt
/frontend
  /app
  /components
  /hooks
  /lib
  /public
  /styles
/docs
  ARCHITECTURE.md
/scripts
README.md
.env.example
.gitignore
```

## Folder Responsibilities
- `backend/app/api`: FastAPI routers and API schemas.
- `backend/app/core`: runtime config, logging, worker lifecycle, and shared helpers.
- `backend/app/db`: Supabase client and query helpers.
- `backend/app/llm`: Gemini client and prompt building.
- `backend/app/retrieval`: keyword extraction and context assembly.
- `backend/app/storage`: S3 helpers and URL resolution.
- `frontend`: Next.js UI and static assets.
- `docs`: architecture and decision notes.

## Key Runtime Flows
- Request flow: HTTP request -> FastAPI route -> retrieval or extraction service -> Supabase/S3 -> response.
- Extraction worker: poll `jobs` -> download media -> Gemini extraction -> write `memory_units` -> mark job complete.
- Voice flow: question -> retrieval -> Gemini answer -> ElevenLabs TTS -> base64 audio response.

## Logging Philosophy
- JSON-formatted logs with request IDs for correlation across API calls.
- `INFO` for lifecycle events (startup, request complete, worker state changes).
- `DEBUG` for diagnostic detail without leaking full prompts, responses, or secrets.
- `WARN/ERROR` for recoverable and fatal failures, respectively.
