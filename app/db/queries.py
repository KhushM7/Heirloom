from __future__ import annotations

import logging
from datetime import datetime
from pprint import pformat

from app.api.schemas import RetrievedMemory
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


def _apply_text_search(query, keywords: list[str]):
    if not keywords:
        return query
    ts_query = " | ".join(keywords)
    try:
        return query.text_search("search_vector", ts_query, config="english")
    except Exception:
        or_clauses = []
        for keyword in keywords:
            or_clauses.extend(
                [
                    f"title.ilike.%{keyword}%",
                    f"summary.ilike.%{keyword}%",
                    f"description.ilike.%{keyword}%",
                ]
            )
        if or_clauses:
            return query.or_(",".join(or_clauses))
    return query


def _apply_keyword_overlap(query, keywords: list[str]):
    if not keywords:
        return query
    keyword_set = ",".join(keywords)
    try:
        return query.or_(f"keywords.cs.{{{keyword_set}}}")
    except Exception:
        return query.contains("keywords", keywords)


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
    profile_id: str, keywords: list[str], event_types: list[str], top_k: int
) -> list[RetrievedMemory]:
    query = (
        supabase.table("memory_units")
        .select(
            "id, title, summary, description, keywords, event_type, places, dates, "
            "media_assets(file_name, mime_type), "
            "citations(id, kind, evidence_text, start_time_ms, end_time_ms, media_asset_id, "
            "media_assets(id, gcs_url))"
        )
        .eq("profile_id", profile_id)
    )

    query = _apply_text_search(query, keywords)
    query = _apply_keyword_overlap(query, keywords)
    query = _apply_event_type_filter(query, event_types)

    response = query.execute()
    data = response.data or []
    print("=== Retrieval Debug: Database Response ===")
    print(pformat(data))
    logger.info(
        "Database retrieval complete.",
        extra={"keyword_filters": keywords, "event_types": event_types, "row_count": len(data)},
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
