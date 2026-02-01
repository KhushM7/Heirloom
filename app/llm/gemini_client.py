from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException, status

from app.core.settings import settings
from app.llm.prompts import (
    EVENT_TYPES,
    KEYWORD_MATCH_SYSTEM_PROMPT,
    KEYWORD_MATCH_USER_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    build_extraction_prompt,
    system_instruction,
)

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency until installed
    genai = None
    types = None


@dataclass
class ExtractedUnit:
    title: str
    summary: str
    description: str | None
    event_type: str
    places: List[str]
    dates: List[str]
    keywords: List[str]


class GeminiClient:
    def __init__(self) -> None:
        if genai is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="google-genai package is not installed",
            )
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing GEMINI_API_KEY",
            )
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def answer_question(self, question: str, context_pack: dict) -> dict:
        """Answer a question using the provided context."""
        context_json = json.dumps(context_pack, ensure_ascii=False)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context_json=context_json)

        response = self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
            },
        )

        text = getattr(response, "text", "") or ""
        parsed = _parse_json_response(text)
        if not parsed:
            return {"answer_text": "I don't know."}
        return {
            "answer_text": parsed.get("answer_text", "I don't know."),
        }

    def match_keywords(
        self, question: str, existing_keywords: list[str], top_n: int = 8
    ) -> list[str]:
        """Match question-derived keywords to existing keyword inventory."""
        existing_keywords_json = json.dumps(existing_keywords, ensure_ascii=False)
        prompt = KEYWORD_MATCH_USER_PROMPT_TEMPLATE.format(
            question=question,
            existing_keywords_json=existing_keywords_json,
            top_n=top_n,
        )

        response = self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={
                "system_instruction": KEYWORD_MATCH_SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        )

        text = getattr(response, "text", "") or ""
        parsed = _parse_json_response(text) or {}
        keywords = parsed.get("keywords", [])
        if not isinstance(keywords, list):
            return []
        return [word for word in keywords if isinstance(word, str)]

    def extract_from_text(self, text: str, modality: str) -> List[ExtractedUnit]:
        """Extract memory units from text content."""
        prompt = build_extraction_prompt(modality)
        response = self._run_with_retries(
            lambda: self._client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[prompt, text],
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=_max_tokens_for_modality(modality),
                    system_instruction=system_instruction(),
                    response_mime_type="application/json",
                ),
            )
        )
        json_payload = _extract_json(response.text or "")
        units = _parse_units(json_payload, response.text or "")
        return _normalize_units(units, modality)

    def extract(self, file_path: str, mime_type: str, modality: str) -> List[ExtractedUnit]:
        """Extract memory units from a file using multimodal input."""
        prompt = build_extraction_prompt(modality)
        upload = self._client.files.upload(file=file_path)
        try:
            upload = self._wait_for_active(upload)
            response = self._run_with_retries(
                lambda: self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=[prompt, upload],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=_max_tokens_for_modality(modality),
                        system_instruction=system_instruction(),
                        response_mime_type="application/json",
                    ),
                )
            )
        finally:
            try:
                self._client.files.delete(name=upload.name)
            except Exception:
                pass

        json_payload = _extract_json(response.text or "")
        units = _parse_units(json_payload, response.text or "")
        return _normalize_units(units, modality)

    def transcribe_media(self, file_path: str, modality: str) -> str:
        """Generate a verbatim transcript of the provided media file."""
        prompt = (
            "Generate a verbatim transcript of the provided media. "
            "Return plain text only."
        )
        upload = self._client.files.upload(file=file_path)
        try:
            upload = self._wait_for_active(upload)
            response = self._run_with_retries(
                lambda: self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=[prompt, upload],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=_max_tokens_for_transcript(modality),
                        system_instruction=system_instruction(),
                        response_mime_type="text/plain",
                    ),
                )
            )
        finally:
            try:
                self._client.files.delete(name=upload.name)
            except Exception:
                pass

        transcript = (response.text or "").strip()
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transcript generation returned empty output",
            )
        return transcript

    def _run_with_retries(self, fn):  # type: ignore[no-untyped-def]
        """Execute a function with exponential backoff retry logic."""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return fn()
            except Exception as exc:  # pragma: no cover - depends on SDK behavior
                last_exc = exc
                # Exponential backoff to smooth over transient failures.
                time.sleep(2 ** attempt)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini request failed: {last_exc}",
        ) from last_exc

    def _wait_for_active(self, uploaded_file: Any) -> Any:
        """Wait for an uploaded file to become ACTIVE."""
        state = getattr(uploaded_file, "state", None)
        name = getattr(uploaded_file, "name", None)
        if not state or not name:
            return uploaded_file
        if getattr(state, "name", None) == "ACTIVE":
            return uploaded_file

        deadline = time.time() + 300
        while time.time() < deadline:
            time.sleep(3)
            refreshed = self._client.files.get(name=name)
            state = getattr(refreshed, "state", None)
            if state and getattr(state, "name", None) == "ACTIVE":
                return refreshed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uploaded file did not become ACTIVE in time",
        )


def _parse_json_response(text: str) -> dict | None:
    """Parse JSON from a text response, with fallback regex extraction."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _extract_json(text: str) -> Any:
    """Extract JSON payload from Gemini response text."""
    if not text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini returned empty response",
        )
    
    # Try to parse the entire response as JSON first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini response missing JSON payload. Response text: {text[:500]}",
        )
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini response JSON could not be parsed. Response text: {text[:500]}",
        ) from exc


def _parse_units(payload: Any, raw_text: str = "") -> List[ExtractedUnit]:
    """Parse memory units from JSON payload."""
    raw_units: Any = None
    if isinstance(payload, list):
        raw_units = payload
    elif isinstance(payload, dict):
        raw_units = payload.get("memory_units")
        if raw_units is None:
            for alt_key in ("memory_unit", "memoryUnits", "units", "memories"):
                if alt_key in payload:
                    raw_units = payload[alt_key]
                    break
        if raw_units is None and ("title" in payload or "summary" in payload):
            raw_units = [payload]

    if isinstance(raw_units, dict):
        raw_units = [raw_units]

    if not isinstance(raw_units, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Gemini response missing memory_units. "
                f"Payload type: {type(payload)}. Raw text: {raw_text[:500]}"
            ),
        )
    
    units: List[ExtractedUnit] = []
    for item in raw_units:
        if not isinstance(item, dict):
            continue
        units.append(
            ExtractedUnit(
                title=str(item.get("title") or "").strip(),
                summary=str(item.get("summary") or "").strip(),
                description=(str(item.get("description")).strip() if item.get("description") else None),
                event_type=str(item.get("event_type") or "Other").strip(),
                places=_ensure_list(item.get("places")),
                dates=_ensure_list(item.get("dates")),
                keywords=_ensure_list(item.get("keywords") or item.get("keywords_array")),
            )
        )
    return units


def _normalize_units(units: List[ExtractedUnit], modality: str) -> List[ExtractedUnit]:
    """Normalize and validate extracted units."""
    modality = modality.lower()
    normalized: List[ExtractedUnit] = []
    for unit in units:
        title = unit.title or "Untitled"
        summary = unit.summary or ""
        event_type = unit.event_type if unit.event_type in EVENT_TYPES else "Other"
        places = unit.places or ["unknown"]
        dates = unit.dates or ["unspecified"]
        keywords = unit.keywords or []

        normalized.append(
            ExtractedUnit(
                title=title,
                summary=summary,
                description=unit.description,
                event_type=event_type,
                places=places,
                dates=dates,
                keywords=keywords,
            )
        )

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extraction produced no memory units",
        )

    # Clamp to a single unit for all modalities per current MVP.
    return normalized[:1]


def _ensure_list(value: Any) -> List[str]:
    """Ensure value is a list of non-empty strings."""
    if isinstance(value, list) and value:
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _mime_for_modality(modality: str) -> str:
    """Get MIME type for a given modality."""
    if modality == "image":
        return "image/jpeg"
    if modality == "video":
        return "video/mp4"
    if modality == "audio":
        return "audio/mpeg"
    if modality == "text":
        return "text/plain"
    return "application/octet-stream"


def _infer_mime_type_from_key(object_key: str | None) -> str | None:
    """Infer MIME type from object key file extension."""
    if not object_key:
        return None
    suffix = Path(object_key).suffix.lower()
    if suffix == ".mp4":
        return "video/mp4"
    if suffix == ".mov":
        return "video/quicktime"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix in {".wav"}:
        return "audio/wav"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".txt":
        return "text/plain"
    if suffix == ".md":
        return "text/markdown"
    return None


def _max_tokens_for_modality(modality: str) -> int:
    """Get maximum output tokens for a given modality."""
    modality = modality.lower()
    if modality == "image":
        return 768
    if modality == "text":
        return 1536
    if modality in {"audio", "video"}:
        return 3072
    return 1024


def _max_tokens_for_transcript(modality: str) -> int:
    """Get maximum output tokens for transcript generation."""
    modality = modality.lower()
    if modality in {"audio", "video"}:
        return 8192
    return 4096
