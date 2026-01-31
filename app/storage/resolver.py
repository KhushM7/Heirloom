"""Asset URL resolution placeholders.

Wire this to your boto3 URL utility to return public or signed URLs.
"""


def resolve_public_url(asset_key: str) -> str:
    """Resolve a public URL for the given asset key.

    Replace the body of this function to call the real boto3 helper.
    """
    return asset_key
