SYSTEM_PROMPT = """You are a grounded assistant. Answer using ONLY the provided context pack.
- If the answer is not contained in the context, say you do not know.
- Do not invent facts.
- Return JSON only with key: answer_text.
"""

USER_PROMPT_TEMPLATE = """Question: {question}

Context pack (JSON):
{context_json}

Return a JSON object with:
- answer_text: string
"""
