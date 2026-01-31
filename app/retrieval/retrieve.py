from __future__ import annotations

from app.api.schemas import CitationOut, ContextPack, RetrievedMemory
from app.core.settings import settings
from app.db.queries import retrieve_memory_units
from app.retrieval.keywords import extract_keywords
from app.storage.resolver import resolve_public_url


def build_context_pack(question: str, retrieved: list[RetrievedMemory]) -> ContextPack:
    memories = []
    for memory in retrieved:
        memory_block = {
            "memory_unit_id": memory.memory_unit_id,
            "title": memory.title,
            "summary": memory.summary,
            "description": memory.description,
            "citations": [
                {
                    "citation_id": citation.citation_id,
                    "kind": citation.kind,
                    "evidence_text": citation.evidence_text,
                    "start_time_ms": citation.start_time_ms,
                    "end_time_ms": citation.end_time_ms,
                    "asset_key": citation.asset_key,
                }
                for citation in memory.citations
            ],
        }
        memories.append(memory_block)
    return ContextPack(question=question, memories=memories)


def retrieve_context(profile_id: str, question: str) -> tuple[ContextPack, list[CitationOut]]:
    extraction = extract_keywords(question)
    keywords = extraction["keywords"]
    retrieved = retrieve_memory_units(profile_id, keywords, settings.DEFAULT_TOP_K)

    context_pack = build_context_pack(question, retrieved)
    citation_outputs: list[CitationOut] = []
    for memory in retrieved:
        for citation in memory.citations:
            asset_url = resolve_public_url(citation.asset_key or "")
            citation_outputs.append(
                CitationOut(
                    citation_id=citation.citation_id,
                    kind=citation.kind,
                    asset_url=asset_url,
                    start_time_ms=citation.start_time_ms,
                    end_time_ms=citation.end_time_ms,
                    evidence_text=citation.evidence_text,
                )
            )

    return context_pack, citation_outputs
