"""Asset URL resolution placeholders.

Wire these helpers to your boto3 URL utility to return public or signed URLs.
"""

from __future__ import annotations

from app.core.settings import settings


def resolve_public_url(asset_key: str) -> str:
    """Resolve a public URL for the given asset key.

    Replace the body of this function to call the real boto3 helper that
    generates public or signed URLs.
    """
    if not asset_key:
        return ""
    base_url = settings.AWS_S3_PUBLIC_BASE_URL
    if base_url:
        return f"{base_url.rstrip('/')}/{asset_key.lstrip('/')}"
    return asset_key
