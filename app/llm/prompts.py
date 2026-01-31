SYSTEM_PROMPT = """You are a grounded assistant. Answer using ONLY the provided context pack.
- If the answer is not contained in the context, say you do not know.
- Do not invent facts.
- Return JSON only with keys: answer_text, used_citation_ids.
"""

USER_PROMPT_TEMPLATE = """Question: {question}

Context pack (JSON):
{context_json}

Return a JSON object with:
- answer_text: string
- used_citation_ids: list of memory_unit_id strings used to support the answer
"""
