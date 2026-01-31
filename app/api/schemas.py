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
