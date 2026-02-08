from __future__ import annotations

import logging

from app.api.schemas import ContextPack, RetrievedMemory
from app.core.settings import settings
from app.db.queries import list_profile_keywords, retrieve_memory_units
from app.retrieval.keywords import extract_keywords
from app.storage.resolver import resolve_public_url

logger = logging.getLogger(__name__)


def build_context_pack(question: str, retrieved: list[RetrievedMemory]) -> ContextPack:
    memories = []
    for memory in retrieved:
        memory_block = {
            "memory_unit_id": memory.memory_unit_id,
            "title": memory.title,
            "summary": memory.summary,
            "description": memory.description,
            "event_type": memory.event_type,
            "places": memory.places,
            "dates": memory.dates,
            "keywords": memory.keywords,
            "asset_key": memory.asset_key,
            "asset_mime_type": memory.asset_mime_type,
        }
        memories.append(memory_block)
    return ContextPack(question=question, memories=memories)


def retrieve_context(
    profile_id: str, question: str
) -> tuple[ContextPack, list[RetrievedMemory], list[dict]]:
    existing_keywords = list_profile_keywords(profile_id)
    extraction = extract_keywords(question, existing_keywords=existing_keywords)
    keywords = extraction["keywords"]
    event_types = extraction["event_types"]
    keyword_matches = extraction.get("keyword_matches", [])

    logger.info(
        "Retrieval keyword extraction complete.",
        extra={
            "keyword_count": len(keywords),
            "event_type_count": len(event_types),
            "keyword_match_count": len(keyword_matches),
        },
    )

    retrieved = retrieve_memory_units(
        profile_id, keywords, event_types, settings.DEFAULT_TOP_K
    )

    context_pack = build_context_pack(question, retrieved)
    return context_pack, retrieved, keyword_matches


def resolve_source_urls(retrieved: list[RetrievedMemory]) -> list[str]:
    urls = []
    for memory in retrieved:
        if not memory.asset_key:
            continue
        urls.append(resolve_public_url(memory.asset_key))
    resolved = sorted(set(urls))
    logger.info(
        "Source URL generation complete.",
        extra={"source_url_count": len(resolved)},
    )
    return resolved
