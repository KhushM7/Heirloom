from __future__ import annotations

from app.api.schemas import RetrievedMemory
from app.db.supabase import supabase


def _apply_text_search(query, keywords: list[str]):
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
    try:
        return query.in_("event_type", event_types)
    except Exception:
        return query.or_(",".join([f"event_type.eq.{event_type}" for event_type in event_types]))


def retrieve_memory_units(
    profile_id: str,
    keywords: list[str],
    event_types: list[str],
    top_k: int,
) -> list[RetrievedMemory]:
    query = (
        supabase.table("memory_units")
        .select(
            "id, title, summary, description, event_type, places, dates, keywords, "
            "media_assets(file_name, mime_type)"
        )
        .eq("profile_id", profile_id)
    )

    query = _apply_text_search(query, keywords)
    query = _apply_keyword_overlap(query, keywords)
    query = _apply_event_type_filter(query, event_types)

    response = query.execute()
    data = response.data or []

    retrieved: list[RetrievedMemory] = []
    for row in data:
        media_asset = row.get("media_assets") or {}
        retrieved.append(
            RetrievedMemory(
                memory_unit_id=row.get("id"),
                title=row.get("title") or "",
                summary=row.get("summary") or "",
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
