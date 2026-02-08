import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.extraction_worker import ExtractionWorker
from app.core.logging import configure_logging, reset_request_id, set_request_id
from app.core.settings import settings

configure_logging()

logger = logging.getLogger("api.request")
worker = ExtractionWorker()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API server for Heirloom project",
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    token = set_request_id(request_id)
    start = perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            "Request failed",
            extra={"method": request.method, "path": request.url.path},
        )
        raise
    finally:
        duration_ms = (perf_counter() - start) * 1000
        status_code = response.status_code if response else 500
        logger.info(
            "Request complete",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        reset_request_id(token)


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
