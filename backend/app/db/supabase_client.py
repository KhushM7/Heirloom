from functools import lru_cache

from supabase import create_client
from supabase.client import Client

from app.core.settings import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
