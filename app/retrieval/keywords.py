from __future__ import annotations

import logging
import re
from collections import Counter

from app.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "about",
    "at",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "as",
    "i",
    "me",
    "my",
    "we",
    "our",
    "you",
    "your",
    "they",
    "their",
    "he",
    "she",
    "his",
    "her",
    "them",
    "what",
    "when",
    "where",
    "who",
    "why",
    "how",
    "did",
}

EVENT_TYPE_MAP = {
    "wedding": "wedding",
    "marriage": "wedding",
    "birthday": "birthday",
    "anniversary": "anniversary",
    "graduation": "graduation",
    "trip": "travel",
    "vacation": "travel",
    "travel": "travel",
    "holiday": "holiday",
    "christmas": "holiday",
    "thanksgiving": "holiday",
    "funeral": "funeral",
}


def _normalize_keywords(words: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for word in words:
        cleaned = word.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _fallback_extract_keywords(question: str, top_n: int) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9']+", question.lower())
    filtered = [token for token in tokens if token not in STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def _match_keywords_with_gemini(
    question: str, existing_keywords: list[str], top_n: int
) -> list[str]:
    if not existing_keywords:
        return []
    client = GeminiClient()
    matched = client.match_keywords(question, existing_keywords, top_n=top_n)
    if not matched:
        return []
    existing_map = {kw.lower(): kw for kw in existing_keywords if isinstance(kw, str)}
    resolved: list[str] = []
    for keyword in matched:
        canonical = existing_map.get(keyword.strip().lower())
        if canonical:
            resolved.append(canonical)
    return _normalize_keywords(resolved)


def extract_keywords(
    question: str, top_n: int = 8, existing_keywords: list[str] | None = None
) -> dict:
    keywords: list[str] = []
    if existing_keywords:
        try:
            keywords = _match_keywords_with_gemini(question, existing_keywords, top_n)
        except Exception as exc:
            logger.warning("Gemini keyword matching failed: %s", exc)

    if not keywords:
        keywords = _fallback_extract_keywords(question, top_n)

    event_types = sorted({EVENT_TYPE_MAP[word] for word in keywords if word in EVENT_TYPE_MAP})
    logger.debug(
        "Keyword extraction complete.",
        extra={
            "question": question,
            "keywords": keywords,
            "event_types": event_types,
            "matched_from_existing": bool(existing_keywords),
        },
    )
    return {"keywords": keywords, "event_types": event_types}
