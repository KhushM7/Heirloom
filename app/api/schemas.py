from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class UploadInitRequest(BaseModel):
    profile_id: str
    file_name: str
    mime_type: str
    bytes: int = Field(..., ge=0)


class UploadInitResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int
    max_bytes: int


class UploadConfirmRequest(BaseModel):
    profile_id: str
    object_key: str
    file_name: str
    mime_type: str
    bytes: Optional[int] = Field(default=None, ge=0)
    duration_seconds: Optional[float] = Field(default=None, ge=0)


class UploadConfirmResponse(BaseModel):
    media_asset_id: str
    job_id: str
    bytes: int


class MediaAssetOut(BaseModel):
    id: str
    profile_id: str
    file_name: str
    mime_type: str
    bytes: int
    duration_seconds: Optional[float] = None


class MemoryUnitOut(BaseModel):
    id: str
    profile_id: str
    media_asset_id: str
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    places: Optional[List[str]] = None
    dates: Optional[List[str]] = None
    keywords: Optional[List[str]] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class CitationOut(BaseModel):
    citation_id: str
    kind: Literal["video_timestamp", "audio_timestamp", "image", "text"]
    asset_url: str
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    evidence_text: str


class AskResponse(BaseModel):
    answer_text: str
    citations: list[CitationOut]


class RetrievedCitation(BaseModel):
    citation_id: str
    kind: str
    evidence_text: str
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    asset_id: str | None = None
    asset_key: str | None = None


class RetrievedMemory(BaseModel):
    memory_unit_id: str
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    created_at: str | None = None
    keywords: list[str] = Field(default_factory=list)
    citations: list[RetrievedCitation] = Field(default_factory=list)


class ContextPack(BaseModel):
    question: str
    memories: list[dict]
