from __future__ import annotations

import logging
from datetime import datetime

from app.api.schemas import RetrievedMemory
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _apply_keyword_filters(query, keywords: list[str]):
    if not keywords:
        return query
    or_clauses = []
    for keyword in keywords:
        or_clauses.extend(
            [
                f"title.ilike.%{keyword}%",
                f"summary.ilike.%{keyword}%",
                f"description.ilike.%{keyword}%",
            ]
        )
    keyword_set = ",".join(keywords)
    or_clauses.append(f"keywords.ov.{{{keyword_set}}}")
    return query.or_(",".join(or_clauses))


def _apply_event_type_filter(query, event_types: list[str]):
    if not event_types:
        return query
    clauses = []
    for event_type in event_types:
        clauses.append(f"event_type.ilike.%{event_type}%")
    if clauses:
        return query.or_(",".join(clauses))
    return query


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def retrieve_memory_units(
    profile_id: str, keywords: list[str], event_types: list[str] | None = None, top_k: int = 10
) -> list[RetrievedMemory]:
    """
    Retrieve memory units with optional event type filtering.

    Args:
        profile_id: User profile identifier
        keywords: List of keywords to search for
        event_types: Optional list of event types to filter by
        top_k: Number of top results to return
    """
    event_types = event_types or []

    supabase = get_supabase_client()
    query = (
        supabase.table("memory_units")
        .select(
            "id, title, summary, description, keywords, event_type, places, dates, "
            "media_assets(file_name, mime_type)"
        )
        .eq("profile_id", profile_id)
    )

    query = _apply_keyword_filters(query, keywords)
    query = _apply_event_type_filter(query, event_types)

    response = query.execute()
    data = response.data or []
    logger.info(
        "Database retrieval complete.",
        extra={
            "keyword_count": len(keywords),
            "event_type_count": len(event_types),
            "row_count": len(data),
        },
    )

    retrieved: list[RetrievedMemory] = []
    for row in data:
        media_asset = row.get("media_assets") or {}
        retrieved.append(
            RetrievedMemory(
                memory_unit_id=row.get("id"),
                title=row.get("title"),
                summary=row.get("summary"),
                description=row.get("description"),
                event_type=row.get("event_type"),
                places=row.get("places") or [],
                dates=row.get("dates") or [],
                keywords=row.get("keywords") or [],
                asset_key=media_asset.get("file_name"),
                asset_mime_type=media_asset.get("mime_type"),
            )
        )

    def score_memory(memory: RetrievedMemory) -> float:
        text_blob = " ".join(
            filter(None, [memory.title, memory.summary, memory.description])
        ).lower()
        keyword_hits = sum(text_blob.count(keyword.lower()) for keyword in keywords)
        keyword_hits += len(set(memory.keywords) & set(keywords)) * 2
        return keyword_hits

    retrieved.sort(key=score_memory, reverse=True)
    return retrieved[:top_k]


def list_profile_keywords(profile_id: str) -> list[str]:
    supabase = get_supabase_client()
    response = (
        supabase.table("memory_units")
        .select("keywords")
        .eq("profile_id", profile_id)
        .execute()
    )
    data = response.data or []
    seen: set[str] = set()
    unique: list[str] = []
    for row in data:
        for keyword in row.get("keywords") or []:
            if not isinstance(keyword, str):
                continue
            cleaned = keyword.strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(cleaned)
    return unique
