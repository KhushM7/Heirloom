# Frontend API Spec (Heirloom)

Base URL: `http://localhost:3000` (dev)
API Prefix: `/api/v1`

All endpoints are JSON unless noted. No auth headers are required in current code.

## Data Extraction

### POST `/api/v1/media-assets/upload-init`
Start an upload by getting a presigned S3 URL.

Request body (`UploadInitRequest`):
```json
{
  "profile_id": "string",
  "file_name": "string",
  "mime_type": "string",
  "bytes": 123
}
```

Response (`UploadInitResponse`):
```json
{
  "upload_url": "string",
  "object_key": "string",
  "object_id": "string",
  "expires_in": 3600,
  "max_bytes": 104857600
}
```

---

### POST `/api/v1/media-assets/upload-confirm`
Confirm upload and enqueue extraction job.

Request body (`UploadConfirmRequest`):
```json
{
  "profile_id": "string",
  "object_id": "string (optional)",
  "object_key": "string",
  "file_name": "string",
  "mime_type": "string",
  "bytes": 123
}
```

Response (`UploadConfirmResponse`):
```json
{
  "media_asset_id": "string",
  "job_id": "string",
  "bytes": 123
}
```

---

### GET `/api/v1/profiles/{profile_id}/media-assets`
List uploaded media assets for a profile.

Response (`MediaAssetOut[]`):
```json
[
  {
    "id": "string",
    "profile_id": "string",
    "file_name": "string",
    "mime_type": "string",
    "bytes": 123
  }
]
```

---

### GET `/api/v1/media-assets/{media_asset_id}/memory-units`
List extracted memory units for a media asset.

Response (`MemoryUnitOut[]`):
```json
[
  {
    "id": "string",
    "profile_id": "string",
    "media_asset_id": "string",
    "title": "string or null",
    "summary": "string or null",
    "description": "string or null",
    "event_type": "string or null",
    "places": ["string"],
    "dates": ["string"],
    "keywords": ["string"]
  }
]
```

---

### PATCH `/api/v1/media-assets/{media_asset_id}/memory-units`
Update fields for memory units tied to a media asset.

Request body (`MemoryUnitUpdateRequest`):
```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "places": ["string"],
  "dates": ["string"]
}
```

Response (`MemoryUnitOut[]`):
```json
[
  {
    "id": "string",
    "profile_id": "string",
    "media_asset_id": "string",
    "title": "string or null",
    "summary": "string or null",
    "description": "string or null",
    "event_type": "string or null",
    "places": ["string"],
    "dates": ["string"],
    "keywords": ["string"]
  }
]
```

---

### GET `/api/v1/profiles/{profile_id}/jobs`
List extraction jobs for a profile.

Response (`JobOut[]`):
```json
[
  {
    "id": "string",
    "profile_id": "string",
    "media_asset_id": "string or null",
    "job_type": "string",
    "status": "string",
    "attempt": 0,
    "error_detail": "string or null",
    "created_at": "string or null",
    "started_at": "string or null",
    "finished_at": "string or null"
  }
]
```

---

### GET `/api/v1/jobs/{job_id}`
Get a specific job by id.

Response (`JobOut`):
```json
{
  "id": "string",
  "profile_id": "string",
  "media_asset_id": "string or null",
  "job_type": "string",
  "status": "string",
  "attempt": 0,
  "error_detail": "string or null",
  "created_at": "string or null",
  "started_at": "string or null",
  "finished_at": "string or null"
}
```

---

### GET `/api/v1/storage/head`
Check object metadata in storage.

Query params:
- `object_key` (string, required)

Response:
```json
{
  "ok": true,
  "bytes": 123,
  "content_type": "string",
  "bucket": "string or null",
  "endpoint": "string or null"
}
```

On error:
```json
{
  "ok": false,
  "error": "string",
  "bucket": "string or null",
  "endpoint": "string or null"
}
```

## Q&A

### POST `/api/v1/profiles/{profile_id}/ask`
Ask a question using extracted memory units.

Request body (`AskRequest`):
```json
{
  "question": "string"
}
```

Response (`AskResponse`):
```json
{
  "answer_text": "string",
  "source_urls": ["string"]
}
```
