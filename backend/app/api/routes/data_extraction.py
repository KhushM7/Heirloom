from fastapi import APIRouter, HTTPException, status
import logging
from uuid import uuid4

from app.api.schemas import (
    JobOut,
    MediaAssetOut,
    MemoryUnitOut,
    MemoryUnitUpdateRequest,
    ProfileCreateRequest,
    ProfileOut,
    UploadConfirmRequest,
    UploadConfirmResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.core.data_extraction import (
    MAX_UPLOAD_BYTES,
    build_object_key,
    create_presigned_upload_url,
    delete_object,
    find_first,
    head_object,
    _s3_client,
    supabase_insert,
    supabase_select,
    supabase_update,
    validate_file_type,
    validate_upload_size,
)
from app.core.settings import settings
from app.storage.resolver import stream_s3_object

router = APIRouter(tags=["data-extraction"])
logger = logging.getLogger(__name__)


def _try_supabase_insert(table: str, payloads: list[dict]) -> dict:
    last_exc: HTTPException | None = None
    for payload in payloads:
        try:
            return supabase_insert(table, payload)
        except HTTPException as exc:
            last_exc = exc
            logger.warning(
                "Supabase insert failed for %s with payload keys=%s: %s",
                table,
                sorted(payload.keys()),
                exc.detail,
            )
    if last_exc:
        raise last_exc
    raise HTTPException(status_code=500, detail="Supabase insert failed")


@router.post("/media-assets/upload-init", response_model=UploadInitResponse)
def upload_init(payload: UploadInitRequest) -> UploadInitResponse:
    validate_upload_size(payload.bytes)
    validate_file_type(payload.file_name, payload.mime_type)

    object_id = uuid4().hex
    object_key = build_object_key(payload.profile_id, payload.file_name, object_id)
    upload_url = create_presigned_upload_url(object_key, payload.mime_type)

    return UploadInitResponse(
        upload_url=upload_url,
        object_key=object_key,
        object_id=object_id,
        expires_in=3600,
        max_bytes=MAX_UPLOAD_BYTES,
    )


@router.post("/media-assets/upload-confirm", response_model=UploadConfirmResponse)
def upload_confirm(payload: UploadConfirmRequest) -> UploadConfirmResponse:
    validate_file_type(payload.file_name, payload.mime_type)

    if payload.object_id:
        expected_key = build_object_key(
            payload.profile_id, payload.file_name, payload.object_id
        )
        if expected_key != payload.object_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="object_key does not match expected naming scheme",
            )

    head = head_object(payload.object_key)
    if head.bytes > MAX_UPLOAD_BYTES:
        delete_object(payload.object_key)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 100 MB limit ({head.bytes} bytes)",
        )

    try:
        existing_assets = supabase_select(
            "media_assets",
            {
                "profile_id": f"eq.{payload.profile_id}",
                "file_name": f"eq.{payload.object_key}",
                "select": "*",
            },
        )
    except HTTPException as exc:
        logger.warning("Supabase select failed for media_assets: %s", exc.detail)
        existing_assets = []
    media_asset = find_first(existing_assets)

    if not media_asset:
        media_payloads = [
            {
                "id": payload.object_id,
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
                "mime_type": payload.mime_type,
                "bytes": head.bytes,
            },
            {
                "id": payload.object_id,
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
                "mime_type": payload.mime_type,
            },
            {
                "id": payload.object_id,
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
                "bytes": head.bytes,
            },
            {
                "id": payload.object_id,
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
            },
            {
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
            },
            {
                "id": payload.object_id,
                "profile_id": payload.profile_id,
                "file_name": payload.file_name,
                "mime_type": payload.mime_type,
                "bytes": head.bytes,
            },
            {
                "profile_id": payload.profile_id,
                "file_name": payload.file_name,
            },
        ]
        media_asset = _try_supabase_insert("media_assets", media_payloads)

    try:
        existing_jobs = supabase_select(
            "jobs",
            {
                "media_asset_id": f"eq.{media_asset['id']}",
                "job_type": "eq.extract",
                "select": "*",
            },
        )
    except HTTPException as exc:
        logger.warning("Supabase select failed for jobs: %s", exc.detail)
        existing_jobs = []
    job = find_first(existing_jobs)

    if not job:
        job_payloads = [
            {
                "profile_id": payload.profile_id,
                "media_asset_id": media_asset["id"],
                "job_type": "extract",
                "status": "queued",
                "attempt": 0,
                "error_detail": None,
            },
            {
                "profile_id": payload.profile_id,
                "media_asset_id": media_asset["id"],
                "job_type": "extract",
                "status": "queued",
                "attempt": 0,
            },
            {
                "profile_id": payload.profile_id,
                "media_asset_id": media_asset["id"],
                "job_type": "extract",
                "status": "queued",
            },
            {
                "profile_id": payload.profile_id,
                "job_type": "extract",
                "status": "queued",
            },
        ]
        job = _try_supabase_insert("jobs", job_payloads)

    return UploadConfirmResponse(
        media_asset_id=str(media_asset["id"]),
        job_id=str(job["id"]),
        bytes=head.bytes,
    )


@router.post("/profiles", response_model=ProfileOut)
def create_profile(payload: ProfileCreateRequest) -> ProfileOut:
    if payload.name:
        try:
            existing = supabase_select(
                "profiles",
                {
                    "name": f"eq.{payload.name}",
                    "select": "*",
                    "limit": 1,
                },
            )
            if existing:
                existing_profile = existing[0]
                if payload.voice_id and not existing_profile.get("voice_id"):
                    try:
                        updated = supabase_update(
                            "profiles",
                            {"voice_id": payload.voice_id},
                            {"id": f"eq.{existing_profile.get('id')}"},
                        )
                        if updated:
                            existing_profile = updated[0]
                    except HTTPException as exc:
                        logger.warning(
                            "Supabase update failed for profiles voice_id: %s", exc.detail
                        )
                return ProfileOut(
                    id=str(existing_profile.get("id")),
                    name=existing_profile.get("name") or payload.name,
                    date_of_birth=existing_profile.get("date_of_birth"),
                    voice_id=existing_profile.get("voice_id") or payload.voice_id,
                )
        except HTTPException:
            # If the profiles table doesn't have a name column, fall back to create.
            pass

    profile_id = payload.profile_id or str(uuid4())
    insert_payload = {"id": profile_id}
    if payload.name:
        insert_payload["name"] = payload.name
    if payload.date_of_birth:
        insert_payload["date_of_birth"] = payload.date_of_birth.isoformat()
    if payload.voice_id:
        insert_payload["voice_id"] = payload.voice_id

    try:
        created = supabase_insert("profiles", insert_payload)
    except HTTPException:
        # Retry with progressively smaller payloads to handle missing columns.
        fallback_payloads = []
        if payload.voice_id:
            payload_with_voice = {"id": profile_id, "voice_id": payload.voice_id}
            if payload.name:
                payload_with_voice["name"] = payload.name
            if payload.date_of_birth:
                payload_with_voice["date_of_birth"] = payload.date_of_birth.isoformat()
            fallback_payloads.append(payload_with_voice)
            fallback_payloads.append(
                {"id": profile_id, "name": payload.name, "voice_id": payload.voice_id}
            )
        if payload.name:
            fallback_payloads.append({"id": profile_id, "name": payload.name})
        fallback_payloads.append({"id": profile_id})
        created = _try_supabase_insert("profiles", fallback_payloads)

    return ProfileOut(
        id=str(created.get("id") or profile_id),
        name=created.get("name") or payload.name,
        date_of_birth=created.get("date_of_birth") or payload.date_of_birth,
        voice_id=created.get("voice_id") or payload.voice_id,
    )


@router.get(
    "/profiles/{profile_id}/media-assets",
    response_model=list[MediaAssetOut],
)
def list_media_assets(profile_id: str) -> list[MediaAssetOut]:
    assets = supabase_select(
        "media_assets",
        {"profile_id": f"eq.{profile_id}", "select": "*", "order": "id.desc"},
    )
    return [MediaAssetOut(**asset) for asset in assets]


@router.get(
    "/media-assets/{media_asset_id}/memory-units",
    response_model=list[MemoryUnitOut],
)
def list_memory_units(media_asset_id: str) -> list[MemoryUnitOut]:
    memory_units = supabase_select(
        "memory_units",
        {
            "media_asset_id": f"eq.{media_asset_id}",
            "select": "*",
        },
    )
    return [MemoryUnitOut(**unit) for unit in memory_units]


@router.patch(
    "/media-assets/{media_asset_id}/memory-units",
    response_model=list[MemoryUnitOut],
)
def update_memory_units(
    media_asset_id: str, payload: MemoryUnitUpdateRequest
) -> list[MemoryUnitOut]:
    update_payload = payload.model_dump(exclude_unset=True)
    if not update_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    updated = supabase_update(
        "memory_units",
        update_payload,
        {"media_asset_id": f"eq.{media_asset_id}"},
    )
    return [MemoryUnitOut(**unit) for unit in updated]


@router.get("/profiles/{profile_id}/jobs", response_model=list[JobOut])
def list_jobs(profile_id: str) -> list[JobOut]:
    jobs = supabase_select(
        "jobs",
        {
            "profile_id": f"eq.{profile_id}",
            "select": "*",
            "order": "created_at.desc",
        },
    )
    return [JobOut(**job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str) -> JobOut:
    jobs = supabase_select(
        "jobs",
        {"id": f"eq.{job_id}", "select": "*", "limit": 1},
    )
    if not jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(**jobs[0])


@router.get("/storage/head")
def storage_head(object_key: str) -> dict:
    try:
        head = head_object(object_key)
    except HTTPException as exc:
        return {
            "ok": False,
            "error": exc.detail,
            "bucket": settings.AWS_S3_BUCKET,
            "endpoint": settings.AWS_S3_ENDPOINT_URL,
        }
    return {
        "ok": True,
        "bytes": head.bytes,
        "content_type": head.content_type,
        "bucket": settings.AWS_S3_BUCKET,
        "endpoint": settings.AWS_S3_ENDPOINT_URL,
    }


@router.get("/storage/stream")
def storage_stream(object_key: str):
    s3_client = _s3_client()
    return stream_s3_object(s3_client=s3_client, key=object_key)
