from fastapi import FastAPI

from app.api.main import api_router
from app.core.extraction_worker import ExtractionWorker

from app.core.settings import settings

worker = ExtractionWorker()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION
)


app.include_router(api_router, prefix=settings.API_V1_STR)