from dotenv import load_dotenv
from os import getenv

load_dotenv()

# How to use:
# Import settings from this module and access the attributes, e.g. settings.AWS_S3_BUCKET
class Settings:
    AWS_ACCESS_KEY_ID: str = getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = getenv("AWS_REGION")
    AWS_S3_BUCKET: str = getenv("AWS_S3_BUCKET")
    AWS_S3_ENDPOINT_URL: str = getenv("AWS_S3_ENDPOINT_URL")
    AWS_S3_PUBLIC_BASE_URL: str = getenv("AWS_S3_PUBLIC_BASE_URL")

    API_V1_STR: str = "/api/v1"

settings = Settings()