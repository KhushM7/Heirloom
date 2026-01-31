from supabase import Client, create_client

from app.core.settings import settings


supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY,
)
