import logging
from os import getenv

from fastapi import FastAPI

from app.api.main import api_router
from app.core.extraction_worker import ExtractionWorker

from app.core.settings import settings

worker = ExtractionWorker()

logging.basicConfig(
    level=getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION
)


app.include_router(api_router, prefix=settings.API_V1_STR)
