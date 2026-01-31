from __future__ import annotations

from datetime import datetime

from app.api.schemas import RetrievedCitation, RetrievedMemory
from app.db.supabase import supabase


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


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def retrieve_memory_units(profile_id: str, keywords: list[str], top_k: int) -> list[RetrievedMemory]:
    query = (
        supabase.table("memory_units")
        .select(
            "id, title, summary, description, created_at, keywords, "
            "citations(id, kind, evidence_text, start_time_ms, end_time_ms, media_asset_id, "
            "media_assets(id, gcs_url))"
        )
        .eq("profile_id", profile_id)
    )

    query = _apply_text_search(query, keywords)
    query = _apply_keyword_overlap(query, keywords)

    response = query.execute()
    data = response.data or []

    retrieved: list[RetrievedMemory] = []
    for row in data:
        citations = []
        for citation in row.get("citations") or []:
            media_asset = citation.get("media_assets") or {}
            citations.append(
                RetrievedCitation(
                    citation_id=citation.get("id"),
                    kind=citation.get("kind") or "text",
                    evidence_text=citation.get("evidence_text") or "",
                    start_time_ms=citation.get("start_time_ms"),
                    end_time_ms=citation.get("end_time_ms"),
                    asset_id=citation.get("media_asset_id"),
                    asset_key=media_asset.get("gcs_url"),
                )
            )
        retrieved.append(
            RetrievedMemory(
                memory_unit_id=row.get("id"),
                title=row.get("title"),
                summary=row.get("summary"),
                description=row.get("description"),
                created_at=row.get("created_at"),
                keywords=row.get("keywords") or [],
                citations=citations,
            )
        )

    def score_memory(memory: RetrievedMemory) -> float:
        text_blob = " ".join(
            filter(None, [memory.title, memory.summary, memory.description])
        ).lower()
        keyword_hits = sum(text_blob.count(keyword.lower()) for keyword in keywords)
        keyword_hits += len(set(memory.keywords) & set(keywords)) * 2
        created_at = _parse_datetime(memory.created_at)
        recency = created_at.timestamp() / 1e10 if created_at else 0.0
        return keyword_hits + recency

    retrieved.sort(key=score_memory, reverse=True)
    return retrieved[:top_k]
