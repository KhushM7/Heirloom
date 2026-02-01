from __future__ import annotations

from datetime import date
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
    object_id: str  # Added from File 2
    expires_in: int
    max_bytes: int


class UploadConfirmRequest(BaseModel):
    profile_id: str
    object_id: Optional[str] = None  # Added from File 2
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
    title: Optional[str] = None  # Made optional from File 2
    summary: Optional[str] = None  # Made optional from File 2
    description: Optional[str] = None
    event_type: Optional[str] = None
    places: Optional[List[str]] = None  # Made optional from File 2
    dates: Optional[List[str]] = None  # Made optional from File 2
    keywords: List[str]


class MemoryUnitUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    places: Optional[List[str]] = None
    dates: Optional[List[str]] = None


class JobOut(BaseModel):  # Added from File 2
    id: str
    profile_id: str
    media_asset_id: Optional[str] = None
    job_type: str
    status: str
    attempt: int
    error_detail: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer_text: str
    source_urls: list[str]  # Kept from File 1


class AskVoiceRequest(BaseModel):
    question: str = Field(..., min_length=1)
    voice_id: Optional[str] = None


class AskVoiceResponse(BaseModel):
    answer_text: str
    source_urls: list[str]
    audio_base64: str
    audio_mime_type: str


class VoiceCloneResponse(BaseModel):
    voice_id: str


class RetrievedMemory(BaseModel):
    memory_unit_id: str
    title: str | None = None  # Made optional from File 2
    summary: str | None = None  # Made optional from File 2
    description: str | None = None
    event_type: str | None = None  # Kept from File 1
    places: list[str] = Field(default_factory=list)  # Kept from File 1
    dates: list[str] = Field(default_factory=list)  # Kept from File 1
    keywords: list[str] = Field(default_factory=list)  # Kept from File 1
    keywords: list[str] = Field(default_factory=list)  # Added from File 2
    asset_key: str | None = None  # Kept from File 1
    asset_mime_type: str | None = None  # Kept from File 1


class ContextPack(BaseModel):
    question: str
    memories: list[dict]


class ProfileCreateRequest(BaseModel):
    profile_id: Optional[str] = None
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    voice_id: Optional[str] = None


class ProfileOut(BaseModel):
    id: str
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    voice_id: Optional[str] = None
