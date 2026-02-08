import base64
import logging

from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from postgrest.exceptions import APIError

from app.api.schemas import AskVoiceRequest, AskVoiceResponse, VoiceCloneResponse
from app.core.settings import settings
from app.core.data_extraction import find_first, supabase_select
from app.elevenLabs.clone_and_tts import (
    clone_voice_from_bytes,
    get_client,
    resolve_voice_id,
    tts_to_bytes,
)
from app.llm.gemini_client import get_gemini_client
from app.retrieval.retrieve import resolve_source_urls, retrieve_context


router = APIRouter(prefix="/profiles", tags=["voice"])
logger = logging.getLogger(__name__)


@router.post("/{profile_id}/ask-voice", response_model=AskVoiceResponse)
async def ask_profile_question_with_voice(
    profile_id: str,
    payload: AskVoiceRequest,
) -> AskVoiceResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Supabase credentials not configured.")
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured.")

    try:
        context_pack, retrieved, keyword_matches = retrieve_context(
            profile_id, payload.question
        )
    except APIError as exc:
        logger.exception("Supabase retrieval failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Supabase query failed: {exc}",
        ) from exc

    if not context_pack.memories:
        return AskVoiceResponse(
            answer_text="I don't know.",
            source_urls=[],
            audio_base64="",
            audio_mime_type="audio/mpeg",
        )

    try:
        gemini_client = get_gemini_client()
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

    answer_text = gemini_response.get("answer_text", "I don't know.")
    source_urls = resolve_source_urls(retrieved)

    profile_voice_id = None
    if not payload.voice_id:
        try:
            profile = find_first(
                supabase_select(
                    "profiles",
                    {
                        "id": f"eq.{profile_id}",
                        "select": "voice_id",
                        "limit": 1,
                    },
                )
            )
        except HTTPException as exc:
            logger.exception("Supabase profile lookup failed.")
            raise HTTPException(
                status_code=502,
                detail=f"Supabase profile lookup failed: {exc.detail}",
            ) from exc
        if profile:
            profile_voice_id = profile.get("voice_id")

    try:
        client = get_client()
        voice_id = resolve_voice_id(payload.voice_id or profile_voice_id)
        audio_bytes = tts_to_bytes(client, voice_id, answer_text)
    except RuntimeError as exc:
        logger.info("Voice ID missing for profile %s.", profile_id)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("ElevenLabs TTS failed.")
        raise HTTPException(
            status_code=502,
            detail=f"ElevenLabs TTS failed: {exc}",
        ) from exc

    return AskVoiceResponse(
        answer_text=answer_text,
        source_urls=source_urls,
        audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
        audio_mime_type="audio/mpeg",
    )


@router.post("/voice-clone", response_model=VoiceCloneResponse)
async def clone_voice_sample(
    sample: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> VoiceCloneResponse:
    if not sample.content_type or not sample.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Audio file is required.")

    try:
        audio_bytes = await sample.read()
        client = get_client()
        voice_id = clone_voice_from_bytes(
            client,
            audio_bytes,
            name=name or "Heirloom Voice",
        )
    except Exception as exc:
        logger.exception("ElevenLabs voice clone failed.")
        raise HTTPException(
            status_code=502,
            detail=f"ElevenLabs voice clone failed: {exc}",
        ) from exc

    return VoiceCloneResponse(voice_id=voice_id)
