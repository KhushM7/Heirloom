import logging

from fastapi import APIRouter, HTTPException
from postgrest.exceptions import APIError

from app.api.schemas import AskRequest, AskResponse
from app.core.settings import settings
from app.llm.gemini_client import GeminiClient
from app.retrieval.retrieve import resolve_source_urls, retrieve_context


router = APIRouter(prefix="/profiles", tags=["qa"])

gemini_client = GeminiClient()
logger = logging.getLogger(__name__)


@router.post("/{profile_id}/ask", response_model=AskResponse)
async def ask_profile_question(profile_id: str, payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured.")
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured.")

    try:
        context_pack, retrieved = retrieve_context(profile_id, payload.question)
    except APIError as exc:
        logger.exception("Supabase retrieval failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Supabase query failed: {exc}",
        ) from exc

    if not context_pack.memories:
        return AskResponse(answer_text="I don't know.", source_urls=[])

    try:
        gemini_response = gemini_client.answer_question(
            question=payload.question,
            context_pack=context_pack.model_dump(),
        )
    except Exception as exc:
        logger.exception("Gemini response failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {exc}",
        ) from exc

    used_ids = set(gemini_response.get("used_citation_ids", []))
    source_urls = resolve_source_urls(retrieved, used_ids)

    return AskResponse(
        answer_text=gemini_response.get("answer_text", "I don't know."),
        source_urls=source_urls,
    )
