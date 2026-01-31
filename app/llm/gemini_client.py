from __future__ import annotations

import json
import re

from google import genai

from app.core.settings import settings
from app.llm.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class GeminiClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def answer_question(self, question: str, context_pack: dict) -> dict:
        context_json = json.dumps(context_pack, ensure_ascii=False)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context_json=context_json)

        response = self._client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
            },
        )

        text = getattr(response, "text", "") or ""
        parsed = _parse_json_response(text)
        if not parsed:
            return {"answer_text": "I don't know.", "used_citation_ids": []}
        return {
            "answer_text": parsed.get("answer_text", "I don't know."),
            "used_citation_ids": parsed.get("used_citation_ids", []),
        }


def _parse_json_response(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
