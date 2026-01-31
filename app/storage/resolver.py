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
