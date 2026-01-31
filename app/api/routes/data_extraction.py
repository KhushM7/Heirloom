from fastapi import APIRouter, HTTPException, status

from app.api.schemas import (
    MediaAssetOut,
    MemoryUnitOut,
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
    supabase_insert,
    supabase_select,
    validate_file_type,
    validate_upload_size,
)

router = APIRouter(tags=["data-extraction"])


@router.post("/media-assets/upload-init", response_model=UploadInitResponse)
def upload_init(payload: UploadInitRequest) -> UploadInitResponse:
    validate_upload_size(payload.bytes)
    validate_file_type(payload.file_name, payload.mime_type)

    object_key = build_object_key(payload.profile_id, payload.file_name)
    upload_url = create_presigned_upload_url(object_key, payload.mime_type)

    return UploadInitResponse(
        upload_url=upload_url,
        object_key=object_key,
        expires_in=3600,
        max_bytes=MAX_UPLOAD_BYTES,
    )


@router.post("/media-assets/upload-confirm", response_model=UploadConfirmResponse)
def upload_confirm(payload: UploadConfirmRequest) -> UploadConfirmResponse:
    validate_file_type(payload.file_name, payload.mime_type)

    head = head_object(payload.object_key)
    if head.bytes > MAX_UPLOAD_BYTES:
        delete_object(payload.object_key)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 500 MB limit ({head.bytes} bytes)",
        )

    existing_assets = supabase_select(
        "media_assets",
        {
            "profile_id": f"eq.{payload.profile_id}",
            "file_name": f"eq.{payload.object_key}",
            "select": "*",
        },
    )
    media_asset = find_first(existing_assets)

    if not media_asset:
        media_asset = supabase_insert(
            "media_assets",
            {
                "profile_id": payload.profile_id,
                "file_name": payload.object_key,
                "mime_type": payload.mime_type,
                "bytes": head.bytes,
                "duration_seconds": payload.duration_seconds,
            },
        )

    existing_jobs = supabase_select(
        "jobs",
        {
            "media_asset_id": f"eq.{media_asset['id']}",
            "job_type": "eq.extract",
            "select": "*",
        },
    )
    job = find_first(existing_jobs)

    if not job:
        job = supabase_insert(
            "jobs",
            {
                "profile_id": payload.profile_id,
                "media_asset_id": media_asset["id"],
                "job_type": "extract",
                "status": "queued",
                "attempt": 0,
                "error_detail": None,
            },
        )

    return UploadConfirmResponse(
        media_asset_id=str(media_asset["id"]),
        job_id=str(job["id"]),
        bytes=head.bytes,
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
            "order": "start_time_ms.asc.nullslast",
        },
    )
    return [MemoryUnitOut(**unit) for unit in memory_units]
