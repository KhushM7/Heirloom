from __future__ import annotations

from typing import List, Optional

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


class MemoryUnitOut(BaseModel):
    id: str
    profile_id: str
    media_asset_id: str
    title: str
    summary: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    places: List[str]
    dates: List[str]
    keywords: List[str]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer_text: str
    source_urls: list[str]


class RetrievedCitation(BaseModel):
    citation_id: str | None = None
    kind: str
    evidence_text: str
    start_time_ms: int | None = None
    end_time_ms: int | None = None
    asset_id: str | None = None
    asset_key: str | None = None


class RetrievedMemory(BaseModel):
    memory_unit_id: str
    title: str
    summary: str
    description: str | None = None
    event_type: str | None = None
    places: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    asset_key: str | None = None
    asset_mime_type: str | None = None


class ContextPack(BaseModel):
    question: str
    memories: list[dict]
