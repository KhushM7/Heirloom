from __future__ import annotations

import logging
import re
from collections import Counter

from app.llm.gemini_client import get_gemini_client

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

RELATEDNESS_THRESHOLD = 8


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
) -> dict:
    if not existing_keywords:
        return {"keywords": [], "matches": []}
    client = get_gemini_client()
    matched = client.match_keywords(question, existing_keywords, top_n=top_n)
    if not matched:
        return {"keywords": [], "matches": []}
    existing_map = {kw.lower(): kw for kw in existing_keywords if isinstance(kw, str)}
    resolved: list[str] = []
    selected_matches: list[dict] = []
    matches = matched.get("matches", [])
    if isinstance(matches, list):
        for item in matches:
            if not isinstance(item, dict):
                continue
            keyword = item.get("keyword")
            if not isinstance(keyword, str):
                continue
            score = item.get("score")
            try:
                score_value = float(score)
            except (TypeError, ValueError):
                continue
            if score_value < RELATEDNESS_THRESHOLD:
                continue
            canonical = existing_map.get(keyword.strip().lower())
            if canonical:
                resolved.append(canonical)
                selected_matches.append(
                    {
                        "keyword": canonical,
                        "score": score_value,
                        "question_keyword": item.get("question_keyword"),
                    }
                )
    if resolved:
        return {
            "keywords": _normalize_keywords(resolved),
            "matches": selected_matches,
        }

    keywords = matched.get("keywords", [])
    if isinstance(keywords, list):
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            canonical = existing_map.get(keyword.strip().lower())
            if canonical:
                resolved.append(canonical)
    if not resolved:
        return {"keywords": [], "matches": []}
    resolved_normalized = _normalize_keywords(resolved)
    question_terms = set(re.findall(r"[a-zA-Z0-9']+", question.lower()))
    strict_matches = []
    for keyword in resolved_normalized:
        kw_terms = re.findall(r"[a-zA-Z0-9']+", keyword.lower())
        if not kw_terms:
            continue
        if any(term in question_terms for term in kw_terms):
            strict_matches.append(keyword)
    return {
        "keywords": strict_matches or resolved_normalized,
        "matches": selected_matches,
    }


def extract_keywords(
    question: str, top_n: int = 8, existing_keywords: list[str] | None = None
) -> dict:
    keywords: list[str] = []
    keyword_matches: list[dict] = []
    if existing_keywords:
        try:
            result = _match_keywords_with_gemini(question, existing_keywords, top_n)
            keywords = result.get("keywords", [])
            keyword_matches = result.get("matches", [])
        except Exception as exc:
            logger.warning("Gemini keyword matching failed: %s", exc)

    if not keywords:
        keywords = _fallback_extract_keywords(question, top_n)

    event_types = sorted({EVENT_TYPE_MAP[word] for word in keywords if word in EVENT_TYPE_MAP})
    logger.debug(
        "Keyword extraction complete.",
        extra={
            "question_length": len(question),
            "keyword_count": len(keywords),
            "event_types": event_types,
            "keyword_match_count": len(keyword_matches),
            "matched_from_existing": bool(existing_keywords),
        },
    )
    return {
        "keywords": keywords,
        "event_types": event_types,
        "keyword_matches": keyword_matches,
    }
