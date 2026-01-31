from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.data_extraction import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_MIME_TYPES,
    delete_object,
    get_object_bytes,
    head_object,
    supabase_insert,
    supabase_select,
    supabase_update,
)

LOGGER = logging.getLogger("extraction-worker")

POLL_INTERVAL_SECONDS = 3
TEXT_CHUNK_SIZE = 1500


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
            try:
                processed = self._process_next_job()
                if not processed:
                    time.sleep(POLL_INTERVAL_SECONDS)
            except Exception:
                LOGGER.exception("Unexpected error in extraction worker")
                time.sleep(POLL_INTERVAL_SECONDS)

    def _process_next_job(self) -> bool:
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
            {"status": "running", "attempt": int(job.get("attempt") or 0) + 1},
            {"id": f"eq.{job['id']}", "status": "eq.queued"},
        )
        if not updated:
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
            {"status": "done", "error_detail": None},
            {"id": f"eq.{job['id']}"},
        )

    def _ensure_object_ok(self, media_asset: Dict[str, Any]) -> None:
        object_key = media_asset.get("file_name")
        if not object_key:
            raise HTTPException(status_code=400, detail="Missing object key")

        head = head_object(object_key)
        if head.bytes > MAX_UPLOAD_BYTES:
            delete_object(object_key)
            raise HTTPException(status_code=413, detail="File exceeds 500 MB limit")

    def _extract_memories(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        mime_type = media_asset.get("mime_type")
        if mime_type.startswith("text/"):
            return self._extract_text(media_asset)
        if mime_type.startswith("image/"):
            return self._extract_image(media_asset)
        if mime_type.startswith("audio/"):
            return self._extract_audio(media_asset)
        if mime_type.startswith("video/"):
            return self._extract_video(media_asset)
        return ExtractionResult(memory_units=[])

    def _extract_text(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        content = self._read_text_object(media_asset)
        chunks = self._chunk_text(content)
        memory_units = []
        for idx, chunk in enumerate(chunks, start=1):
            title = f"Text Chunk {idx}"
            summary = chunk[:200].strip() or "(empty)"
            memory_units.append(
                {
                    "profile_id": media_asset["profile_id"],
                    "media_asset_id": media_asset["id"],
                    "title": title,
                    "summary": summary,
                    "description": chunk.strip() or None,
                    "event_type": "Other",
                    "places": ["unknown"],
                    "dates": ["unspecified"],
                    "keywords": [],
                }
            )
        return ExtractionResult(memory_units=memory_units)

    def _extract_image(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        memory_units = [
            {
                "profile_id": media_asset["profile_id"],
                "media_asset_id": media_asset["id"],
                "title": "Image Memory",
                "summary": "Image uploaded.",
                "description": "Image content not analyzed.",
                "event_type": "Other",
                "places": ["unknown"],
                "dates": ["unspecified"],
                "keywords": [],
            }
        ]
        return ExtractionResult(memory_units=memory_units)

    def _extract_audio(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        memory_units = [
            {
                "profile_id": media_asset["profile_id"],
                "media_asset_id": media_asset["id"],
                "title": "Audio Memory",
                "summary": "Audio uploaded.",
                "description": "Audio transcript not analyzed.",
                "event_type": "Other",
                "places": ["unknown"],
                "dates": ["unspecified"],
                "keywords": [],
            }
        ]
        return ExtractionResult(memory_units=memory_units)

    def _extract_video(self, media_asset: Dict[str, Any]) -> ExtractionResult:
        memory_units = [
            {
                "profile_id": media_asset["profile_id"],
                "media_asset_id": media_asset["id"],
                "title": "Video Memory",
                "summary": "Video uploaded.",
                "description": "Video content not analyzed.",
                "event_type": "Other",
                "places": ["unknown"],
                "dates": ["unspecified"],
                "keywords": [],
            }
        ]
        return ExtractionResult(memory_units=memory_units)

    def _read_text_object(self, media_asset: Dict[str, Any]) -> str:
        object_key = media_asset.get("file_name")
        payload = get_object_bytes(object_key)
        return payload.decode("utf-8", errors="replace")

    @staticmethod
    def _chunk_text(content: str) -> List[str]:
        if not content:
            return [""]
        chunks = []
        start = 0
        while start < len(content):
            end = min(start + TEXT_CHUNK_SIZE, len(content))
            chunks.append(content[start:end])
            start = end
        return chunks

    def _persist_results(
        self, media_asset: Dict[str, Any], extraction: ExtractionResult
    ) -> tuple[int, int]:
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

            supabase_insert("memory_units", unit)
            inserted_count += 1
            existing_keys.add(key)

        return inserted_count, len(existing_units)

    @staticmethod
    def _memory_key(media_asset: Dict[str, Any], unit: Dict[str, Any]) -> Optional[str]:
        title = unit.get("title")
        if not title:
            return None
        return f"{media_asset['id']}:{title}"

    def _mark_failed(self, job: Dict[str, Any], detail: str) -> None:
        supabase_update(
            "jobs",
            {"status": "failed", "error_detail": detail},
            {"id": f"eq.{job['id']}"},
        )
