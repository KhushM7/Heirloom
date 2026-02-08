from __future__ import annotations

from typing import Dict

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError

from app.core.settings import settings

# Explicit mime mapping for your allowed file types
_MIME_BY_EXT: Dict[str, str] = {
    "mp4": "video/mp4",
    "mp3": "audio/mpeg",
    "txt": "text/plain",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


def stream_s3_object(*, s3_client, key: str) -> StreamingResponse:
    """
    Streams mp4/mp3/txt/jpg/png directly from S3 using get_object.
    Auto-sets Content-Type and inline rendering based on file extension.
    """

    if not key:
        raise HTTPException(status_code=400, detail="Missing S3 key")

    if not settings.AWS_S3_BUCKET:
        raise HTTPException(status_code=500, detail="AWS_S3_BUCKET not configured")

    ext = key.rsplit(".", 1)[-1].lower()
    media_type = _MIME_BY_EXT.get(ext)

    if not media_type:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: .{ext}"
        )

    try:
        response = s3_client.get_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key
        )
    except ClientError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": f'inline; filename="{key}"'
    }

    return StreamingResponse(
        response["Body"],
        media_type=media_type,
        headers=headers,
    )


def resolve_public_url(key: str) -> str:
    """
    Converts an S3 key to a publicly accessible URL.

    Priority:
    1. Generate a presigned URL (temporary, works for private buckets)
    2. Fallback to s3:// URI if all else fails
    """
    if not key:
        return ""

    # First priority: generate presigned URL
    from app.core.data_extraction import _s3_client
    try:
        s3_client = _s3_client()
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_S3_BUCKET,
                'Key': key
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )
        return presigned_url
    except Exception as e:
        # Log the error but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate presigned URL for {key}: {e}")

        # Fallback to s3:// URI
        if settings.AWS_S3_BUCKET:
            return f"s3://{settings.AWS_S3_BUCKET}/{key}"
        return key
