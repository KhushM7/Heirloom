import logging
from os import getenv

from fastapi import FastAPI

from api.main import api_router
from core.extraction_worker import ExtractionWorker
from core.settings import settings

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

@app.on_event("startup")
def start_extraction_worker() -> None:
    worker.start()


@app.on_event("shutdown")
def stop_extraction_worker() -> None:
    worker.stop()

@app.get("/api/v1/worker/status")
def worker_status() -> dict:
    """Get the current status of the extraction worker."""
    return worker.status()


@app.post("/api/v1/worker/start")
def worker_start() -> dict:
    """Start the extraction worker."""
    worker.start()
    return worker.status()


@app.post("/api/v1/worker/stop")
def worker_stop() -> dict:
    """Stop the extraction worker."""
    worker.stop()
    return worker.status()