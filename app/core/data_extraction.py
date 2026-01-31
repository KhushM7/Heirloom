from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable
from uuid import uuid4

import boto3
import httpx
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from app.core.settings import settings

MAX_UPLOAD_BYTES = 500 * 1024 * 1024

SUPPORTED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "image/png",
    "image/jpeg",
    "image/webp",
    "text/plain",
    "text/markdown",
}

SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mp3",
    ".wav",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".txt",
    ".md",
}


@dataclass(frozen=True)
class UploadHead:
    bytes: int
    content_type: str | None


def _require_setting(value: str | None, name: str) -> str:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing required setting: {name}",
        )
    return value


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=_require_setting(settings.AWS_ACCESS_KEY_ID, "AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_require_setting(
            settings.AWS_SECRET_ACCESS_KEY, "AWS_SECRET_ACCESS_KEY"
        ),
        region_name=_require_setting(settings.AWS_REGION, "AWS_REGION"),
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
    )


def _supabase_headers() -> Dict[str, str]:
    key = _require_setting(settings.SUPABASE_SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _supabase_url(table: str) -> str:
    base = _require_setting(settings.SUPABASE_URL, "SUPABASE_URL").rstrip("/")
    return f"{base}/rest/v1/{table}"


def validate_upload_size(bytes_size: int) -> None:
    if bytes_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 500 MB limit ({bytes_size} bytes)",
        )


def validate_file_type(file_name: str, mime_type: str) -> None:
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mime type: {mime_type}",
        )
    extension = Path(file_name).suffix.lower()
    if extension and extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension}",
        )


def build_object_key(profile_id: str, file_name: str) -> str:
    safe_name = Path(file_name).name
    token = uuid4().hex
    return f"profiles/{profile_id}/{token}_{safe_name}"


def create_presigned_upload_url(object_key: str, mime_type: str) -> str:
    client = _s3_client()
    bucket = _require_setting(settings.AWS_S3_BUCKET, "AWS_S3_BUCKET")
    try:
        return client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": object_key,
                "ContentType": mime_type,
            },
            ExpiresIn=3600,
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create upload URL",
        ) from exc


def head_object(object_key: str) -> UploadHead:
    client = _s3_client()
    bucket = _require_setting(settings.AWS_S3_BUCKET, "AWS_S3_BUCKET")
    try:
        response = client.head_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uploaded object not found",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded object metadata",
        ) from exc

    return UploadHead(
        bytes=int(response.get("ContentLength", 0)),
        content_type=response.get("ContentType"),
    )


def get_object_bytes(object_key: str) -> bytes:
    client = _s3_client()
    bucket = _require_setting(settings.AWS_S3_BUCKET, "AWS_S3_BUCKET")
    try:
        response = client.get_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded object",
        ) from exc
    body = response.get("Body")
    if not body:
        return b""
    return body.read()


def delete_object(object_key: str) -> None:
    client = _s3_client()
    bucket = _require_setting(settings.AWS_S3_BUCKET, "AWS_S3_BUCKET")
    try:
        client.delete_object(Bucket=bucket, Key=object_key)
    except ClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete oversized object",
        ) from exc


def supabase_select(table: str, params: Dict[str, Any]) -> list[dict[str, Any]]:
    url = _supabase_url(table)
    response = httpx.get(url, headers=_supabase_headers(), params=params, timeout=30.0)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase read failed: {response.text}",
        )
    return response.json()


def supabase_insert(table: str, payload: Dict[str, Any]) -> dict[str, Any]:
    url = _supabase_url(table)
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase insert failed: {response.text}",
        )
    data = response.json()
    if isinstance(data, list):
        return data[0] if data else {}
    return data


def supabase_update(
    table: str, payload: Dict[str, Any], filters: Dict[str, Any]
) -> list[dict[str, Any]]:
    url = _supabase_url(table)
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    response = httpx.patch(url, headers=headers, params=filters, json=payload, timeout=30.0)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase update failed: {response.text}",
        )
    data = response.json()
    return data if isinstance(data, list) else []


def find_first(items: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        return item
    return None
