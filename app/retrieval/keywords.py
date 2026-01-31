from __future__ import annotations

import logging
import re
from collections import Counter

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


def extract_keywords(question: str, top_n: int = 8) -> dict:
    tokens = re.findall(r"[a-zA-Z0-9']+", question.lower())
    filtered = [token for token in tokens if token not in STOPWORDS]
    counts = Counter(filtered)
    keywords = [word for word, _ in counts.most_common(top_n)]
    event_types = sorted({EVENT_TYPE_MAP[word] for word in keywords if word in EVENT_TYPE_MAP})
    logger.debug(
        "Keyword extraction complete.",
        extra={"question": question, "keywords": keywords, "event_types": event_types},
    )
    return {"keywords": keywords, "event_types": event_types}
