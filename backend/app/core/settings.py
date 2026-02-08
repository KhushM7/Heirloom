from pathlib import Path
from os import getenv

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")


class Settings:
    # =========================
    # AWS / S3
    # =========================
    AWS_ACCESS_KEY_ID: str = getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = getenv("AWS_REGION")
    AWS_S3_BUCKET: str = getenv("AWS_S3_BUCKET")
    AWS_S3_ENDPOINT_URL: str = getenv("AWS_S3_ENDPOINT_URL")

    # =========================
    # Gemini (LLM)
    # =========================
    GEMINI_API_KEY: str = getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = getenv("GEMINI_MODEL", "gemini-2.5-pro")

    # =========================
    # Supabase (DB)
    # =========================
    SUPABASE_URL: str = getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = getenv("SUPABASE_SERVICE_ROLE_KEY")

    # =========================
    # API metadata
    # =========================
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Heirloom API"
    VERSION: str = "0.1.0"

    # =========================
    # Retrieval / Q&A config
    # =========================
    DEFAULT_TOP_K: int = int(getenv("DEFAULT_TOP_K", "8"))

    # =========================
    # CORS
    # =========================
    CORS_ALLOW_ORIGINS: str = getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000")


settings = Settings()
