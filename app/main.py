from fastapi import FastAPI

from app.api.routes import api_router
from app.core.extraction_worker import ExtractionWorker
from app.core.settings import settings

worker = ExtractionWorker()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION
)


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def start_worker() -> None:
    worker.start()


@app.on_event("shutdown")
def stop_worker() -> None:
    worker.stop()
