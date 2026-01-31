from fastapi import APIRouter, HTTPException

from app.api.schemas import AskRequest, AskResponse
from app.llm.gemini_client import GeminiClient
from app.retrieval.retrieve import resolve_source_urls, retrieve_context


router = APIRouter(prefix="/profiles", tags=["qa"])

gemini_client = GeminiClient()


@router.post("/{profile_id}/ask", response_model=AskResponse)
async def ask_profile_question(profile_id: str, payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    context_pack, retrieved = retrieve_context(profile_id, payload.question)

    if not context_pack.memories:
        return AskResponse(answer_text="I don't know.", source_urls=[])

    gemini_response = gemini_client.answer_question(
        question=payload.question,
        context_pack=context_pack.model_dump(),
    )

    used_ids = set(gemini_response.get("used_citation_ids", []))
    source_urls = resolve_source_urls(retrieved, used_ids)

    return AskResponse(
        answer_text=gemini_response.get("answer_text", "I don't know."),
        source_urls=source_urls,
    )
