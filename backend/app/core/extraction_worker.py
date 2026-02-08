from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm.gemini_client import GeminiClient, get_gemini_client
from fastapi import HTTPException

from app.core.data_extraction import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_MIME_TYPES,
    delete_object,
    download_object_to_path,
    head_object,
    supabase_insert,
    supabase_select,
    supabase_update,
)


LOGGER = logging.getLogger("extraction-worker")

POLL_INTERVAL_SECONDS = 3


@dataclass
class ExtractionResult:
    memory_units: List[Dict[str, Any]]


class WorkerStop:
    def __init__(self) -> None:
        self._event = threading.Event()

    def stop(self) -> None:
        self._event.set()

    def should_stop(self) -> bool:
        return self._event.is_set()


class ExtractionWorker:
    def __init__(self) -> None:
        self._stop = WorkerStop()
        self._thread: Optional[threading.Thread] = None
        self._last_error: str | None = None
        self._last_tick: float | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.stop()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.should_stop():
            self._last_tick = time.time()
            try:
                processed = self._process_next_job()
                if not processed:
                    # Back off when there is no work to avoid hot-looping.
                    time.sleep(POLL_INTERVAL_SECONDS)
            except Exception:
                self._last_error = "Unexpected error in extraction worker"
                LOGGER.exception("Unexpected error in extraction worker")
                time.sleep(POLL_INTERVAL_SECONDS)

    def status(self) -> dict:
        return {
            "alive": bool(self._thread and self._thread.is_alive()),
            "last_error": self._last_error,
            "last_tick": self._last_tick,
        }

    def _process_next_job(self) -> bool:
        # Pull a single queued job; optimistic update claims it.
        jobs = supabase_select(
            "jobs",
            {
                "status": "eq.queued",
                "job_type": "eq.extract",
                "order": "id.asc",
                "limit": 1,
            },
        )
        if not jobs:
            return False

        job = jobs[0]
        updated = supabase_update(
            "jobs",
            {
                "status": "running",
                "attempt": int(job.get("attempt") or 0) + 1,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            {"id": f"eq.{job['id']}", "status": "eq.queued"},
        )
        if not updated:
            # Another worker claimed it first.
            return False

        try:
            self._handle_job(updated[0])
        except HTTPException as exc:
            LOGGER.warning("Job failed: %s", exc.detail)
            self._mark_failed(job, str(exc.detail))
        except Exception as exc:
            LOGGER.exception("Job failed")
            self._mark_failed(job, f"Unexpected error: {exc}")
        return True

    def _handle_job(self, job: Dict[str, Any]) -> None:
        media_assets = supabase_select(
            "media_assets",
            {"id": f"eq.{job['media_asset_id']}", "select": "*", "limit": 1},
        )
        if not media_assets:
            raise HTTPException(status_code=400, detail="Missing media asset")
        media_asset = media_assets[0]

        mime_type = media_asset.get("mime_type")
        if mime_type not in SUPPORTED_MIME_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported mime type: {mime_type}")

        self._ensure_object_ok(media_asset)

        extraction = self._extract_memories(media_asset)
        if not extraction.memory_units:
            raise HTTPException(status_code=400, detail="No memory units produced")

        inserted_count, existing_count = self._persist_results(media_asset, extraction)
        if inserted_count == 0 and existing_count == 0:
            raise HTTPException(status_code=400, detail="No memory units written")

        supabase_update(
            "jobs",
            {
                "status": "done",
                "error_detail": None,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            {"id": f"eq.{job['id']}"},
        )

    def _ensure_object_ok(self, media_asset: Dict[str, Any]) -> None:
        object_key = media_asset.get("file_name")
        if not object_key:
            raise HTTPException(status_code=400, detail="Missing object key")

        head = head_object(object_key)
        if head.bytes > MAX_UPLOAD_BYTES:
            # Enforce hard size limit by deleting oversized objects.
            delete_object(object_key)
            raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")

    def _extract_memories(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        object_key = media_asset.get("file_name")
        if not object_key:
            raise HTTPException(status_code=400, detail="Missing object key")

        client = get_gemini_client()
        modality = self._modality(media_asset.get("mime_type"))

        if modality == "text":
            return self._extract_text_single_pass(media_asset, client)

        suffix = self._suffix_for_mime(media_asset.get("mime_type"))
        temp_path = Path(f"/tmp/{media_asset['id']}{suffix}")
        download_object_to_path(object_key, str(temp_path))
        try:
            if modality == "audio":
                transcript = client.transcribe_media(str(temp_path), modality)
                units = self._extract_from_transcript(transcript, modality, client)
            else:
                units = client.extract(
                    file_path=str(temp_path),
                    mime_type=media_asset.get("mime_type"),
                    modality=modality,
                )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                LOGGER.warning("Failed to delete temp file %s", temp_path)

        return self._build_results(media_asset, units)

    def _extract_text_single_pass(
        self, media_asset: Dict[str, Any], client: GeminiClient
    ) -> ExtractionResult:
        object_key = media_asset.get("file_name")
        temp_path = Path(f"/tmp/{media_asset['id']}.txt")
        download_object_to_path(object_key, str(temp_path))
        try:
            content = temp_path.read_text(encoding="utf-8", errors="replace")
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                LOGGER.warning("Failed to delete temp file %s", temp_path)

        units = client.extract_from_text(content, "text")
        return self._build_results(media_asset, units)

    def _extract_from_transcript(
        self, transcript: str, modality: str, client: GeminiClient
    ) -> List[Any]:
        return client.extract_from_text(transcript, modality)

    @staticmethod
    def _suffix_for_mime(mime_type: str | None) -> str:
        if not mime_type:
            return ""
        if mime_type == "video/mp4":
            return ".mp4"
        if mime_type == "video/quicktime":
            return ".mov"
        if mime_type == "audio/mpeg":
            return ".mp3"
        if mime_type in {"audio/wav", "audio/x-wav"}:
            return ".wav"
        if mime_type == "image/png":
            return ".png"
        if mime_type == "image/jpeg":
            return ".jpg"
        if mime_type == "image/webp":
            return ".webp"
        if mime_type == "text/plain":
            return ".txt"
        if mime_type == "text/markdown":
            return ".md"
        return ""

    @staticmethod
    def _modality(mime_type: str | None) -> str:
        if not mime_type:
            return "unknown"
        if mime_type.startswith("text/"):
            return "text"
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("audio/"):
            return "audio"
        if mime_type.startswith("video/"):
            return "video"
        return "unknown"

    def _build_results(
        self, media_asset: Dict[str, Any], units: List[Any]
    ) -> ExtractionResult:
        memory_units = []
        for unit in units:
            memory_units.append(
                {
                    "profile_id": media_asset["profile_id"],
                    "media_asset_id": media_asset["id"],
                    "title": unit.title,
                    "summary": unit.summary,
                    "description": unit.description,
                    "event_type": unit.event_type,
                    "places": unit.places,
                    "dates": unit.dates,
                    "keywords": unit.keywords,
                }
            )
        return ExtractionResult(memory_units=memory_units)

    def _persist_results(
        self, media_asset: Dict[str, Any], extraction: ExtractionResult
    ) -> tuple[int, int]:
        # Build idempotency keys so retries don't duplicate memory units.
        existing_units = supabase_select(
            "memory_units",
            {"media_asset_id": f"eq.{media_asset['id']}", "select": "*"},
        )
        existing_keys = set()
        for unit in existing_units:
            key = self._memory_key(media_asset, unit)
            if key:
                existing_keys.add(key)

        inserted_count = 0
        for unit in extraction.memory_units:
            key = self._memory_key(media_asset, unit)
            if key and key in existing_keys:
                continue

            new_unit = supabase_insert("memory_units", unit)
            inserted_count += 1
            existing_keys.add(key)

        return inserted_count, len(existing_units)

    @staticmethod
    def _memory_key(media_asset: Dict[str, Any], unit: Dict[str, Any]) -> Optional[str]:
        mime_type = media_asset.get("mime_type")
        if mime_type:
            return f"{media_asset['id']}:{unit.get('title')}"
        return None

    def _mark_failed(self, job: Dict[str, Any], detail: str) -> None:
        supabase_update(
            "jobs",
            {
                "status": "failed",
                "error_detail": detail,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
            {"id": f"eq.{job['id']}"},
        )

