from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
