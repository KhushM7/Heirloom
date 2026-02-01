from __future__ import annotations

# Question-answering prompts
SYSTEM_PROMPT = """You are a grounded, immersive narrator. Answer using ONLY the provided context pack.
- If the answer is not contained in the context, say "I don't know."
- If the context is related to the topic but does NOT answer the exact question, say: "I can't remember the answer to your exact question, but I do remember [something else relevant to the topic...]" and then include the relevant detail from the context.
- Do not invent facts or add details that are not present.
- Write in the first person, with a warm, descriptive, sensory tone while staying faithful to the facts.
- Keep it concise (2-4 sentences).
- Return JSON only with key: answer_text.
"""

USER_PROMPT_TEMPLATE = """Question: {question}

Context pack (JSON):
{context_json}

Write a vivid, scene-like response grounded in the context pack.
Return a JSON object with:
- answer_text: string
"""

KEYWORD_MATCH_SYSTEM_PROMPT = (
    "You are a retrieval assistant. Match user questions to existing keywords. "
    "Return JSON only."
)

KEYWORD_MATCH_USER_PROMPT_TEMPLATE = """Question: {question}

Existing keywords (JSON array):
{existing_keywords_json}

Task:
1) Infer up to {top_n} short keywords/phrases from the question (lowercase, 1-3 words).
2) From the existing keywords list, select only those that are exact matches or near-exact matches (same root/lemma).

Rules:
- Output keywords MUST be items from the existing list.
- Do NOT return broad or loosely related terms.
- Return JSON only: {{"keywords": []}}
"""

# Extraction configuration
EVENT_TYPES = [
    "BirthChildhood",
    "School",
    "Graduation",
    "Career",
    "MovingMigration",
    "Relationship",
    "Marriage",
    "ChildrenFamily",
    "Travel",
    "TraditionHoliday",
    "AdviceValues",
    "FunnyAnecdote",
    "LossGrief",
    "Health",
    "HistoricalWitness",
    "HobbyPassion",
    "Other",
]


def system_instruction() -> str:
    """System instruction for extraction tasks."""
    return (
        "You are a careful data extraction system. "
        "Only use facts visible or clearly stated in the provided content. "
        "Do not infer details that are not present. "
        "Return only JSON with no extra text."
    )


def build_extraction_prompt(modality: str) -> str:
    """Build extraction prompt based on content modality."""
    modality = modality.lower()
    # Keep modality rules compact but explicit to reduce retries.
    modality_rules = ""
    if modality == "image":
        modality_rules = "Return exactly 1 memory_unit."

    return (
        "Extract grounded memory units for the database.\n"
        f"Modality: {modality}.\n"
        "Rules:\n"
        "- No invented facts. Only use what is present or strongly implied.\n"
        f"- {modality_rules}\n"
        "- places and dates must be non-empty arrays; use 'unknown' or 'unspecified' if missing.\n"
        "- event_type must be one of: "
        + ", ".join(EVENT_TYPES)
        + ".\n"
        "- Add useful keywords/tags for retrieval (short phrases). Use keywords.\n"
        "Return JSON ONLY:\n"
        '{\"memory_units\":[{\"title\":\"\",\"summary\":\"\",\"description\":null,'
        '\"event_type\":\"Other\",\"places\":[\"\"],\"dates\":[\"\"],\"keywords\":[]}]}'
    )
