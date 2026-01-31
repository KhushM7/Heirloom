from __future__ import annotations

import logging
from pprint import pformat

from app.api.schemas import ContextPack, RetrievedMemory
from app.core.settings import settings
from app.db.queries import retrieve_memory_units
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


def retrieve_context(profile_id: str, question: str) -> tuple[ContextPack, list[RetrievedMemory]]:
    extraction = extract_keywords(question)
    keywords = extraction["keywords"]
    event_types = extraction["event_types"]
    print("=== Retrieval Debug: Keyword Extraction ===")
    print(f"Question: {question}")
    print(f"Keywords: {keywords}")
    print(f"Matched tags/event types: {event_types}")
    logger.info(
        "Retrieval keyword extraction complete.",
        extra={"question": question, "keywords": keywords, "event_types": event_types},
    )
    retrieved = retrieve_memory_units(
        profile_id, keywords, event_types, settings.DEFAULT_TOP_K
    )

    context_pack = build_context_pack(question, retrieved)
    return context_pack, retrieved


def resolve_source_urls(
    retrieved: list[RetrievedMemory], used_ids: set[str]
) -> list[str]:
    urls = []
    for memory in retrieved:
        if memory.memory_unit_id not in used_ids:
            continue
        if not memory.asset_key:
            continue
        urls.append(resolve_public_url(memory.asset_key))
    resolved = sorted(set(urls))
    print("=== Retrieval Debug: Source URL Generation ===")
    print(f"Used citation IDs: {sorted(used_ids)}")
    print(f"Generated URLs: {pformat(resolved)}")
    logger.info(
        "Source URL generation complete.",
        extra={"used_ids": sorted(used_ids), "source_urls": resolved},
    )
    return resolved
